"""
AgentTrek Exploration Adapter.

ARCHITECTURE:
This adapter serves as a bridge between the exploration pipeline and AgentTrek.
It forwards semantic actions to AgentTrek, which performs grounding internally.

RESPONSIBILITIES:
- Forward semantic actions (intent, object, context) to AgentTrek
- Forward grounding_hints as soft guidance (AgentTrek decides how to use them)
- Report execution success/failure back to exploration pipeline
- Track screen state changes after actions

ANTI-RESPONSIBILITIES (AgentTrek handles these):
- NO CSS selector generation
- NO DOM querying or element scoring
- NO Playwright locator usage
- NO fallback click logic

AgentTrek owns all grounding and execution decisions.
"""

import logging
from typing import Optional, List, Dict, Any
import json
import re

from exploration.exploration_bridge import ExplorationAdapter
from exploration.schema import ActionSemantic
from exploration.semantic_normalization import normalize_semantic, safe_get_description
from schema import Action, ActionType
from utils.env import env

logger = logging.getLogger(__name__)


class AgentTrekExplorationAdapter(ExplorationAdapter):
    """
    Thin adapter that forwards semantic actions to AgentTrek.

    AgentTrek handles all grounding, element selection, and execution.
    This adapter only manages communication and reports results.

    FORWARDING PROTOCOL:
    1. Receive ActionSemantic with optional GroundingHints
    2. Package as AgentTrek-compatible message
    3. Forward to AgentTrek executor
    4. Observe screen state changes
    5. Report success/failure
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2
    ):
        """
        Initialize AgentTrek exploration adapter.

        Args:
            model_name: HuggingFace model (e.g., "meta-llama/Llama-3.1-8B-Instruct")
            base_url: API base URL (e.g., "https://api-inference.huggingface.co/v1")
            api_key: HuggingFace API key
            temperature: LLM temperature
        """
        super().__init__("agenttrek")

        # Load configuration from .env if not provided.
        # Prefer explicit Explorer/HuggingFace credentials; fallback to OpenAI credentials.
        explorer_api_key = api_key or env.get("EXPLORER_API_KEY") or env.get("HUGGINGFACE_API_KEY")
        openai_api_key = env.get("OPENAI_API_KEY")

        if explorer_api_key:
            self.model_name = model_name or env.get("EXPLORER_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
            self.base_url = base_url or env.get("EXPLORER_BASE_URL", "https://router.huggingface.co/v1")
            self.api_key = explorer_api_key
        else:
            self.model_name = model_name or env.get("OPENAI_MODEL") or env.get("LLM_MODEL", "gpt-4o-mini")
            self.base_url = base_url or env.get("OPENAI_BASE_URL")
            self.api_key = openai_api_key

        self.temperature = temperature or env.get_float("EXPLORER_TEMPERATURE", 0.2)

        # Validate configuration
        if not self.api_key:
            logger.warning(
                "No API key found. Set EXPLORER_API_KEY/HUGGINGFACE_API_KEY or OPENAI_API_KEY in .env"
            )

        # Initialize OpenAI client (compatible with HuggingFace)
        self._client = None
        self._init_client()

        logger.info(f"AgentTrekExplorationAdapter initialized:")
        logger.info(f"  Model: {self.model_name}")
        logger.info(f"  Base URL: {self.base_url or 'https://api.openai.com/v1 (default)'}")
        logger.info(f"  Temperature: {self.temperature}")

    def _init_client(self):
        """Initialize OpenAI-compatible client for HuggingFace."""
        try:
            from openai import OpenAI

            if not self.api_key:
                logger.warning("No API key - client will fail on actual calls")
                return

            client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            self._client = OpenAI(**client_kwargs)
            logger.debug("OpenAI-compatible client initialized")

        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            self._client = None

    async def execute_action(self, action_semantic: ActionSemantic, env) -> bool:
        """
        Forward semantic action to AgentTrek for execution.

        This method packages the semantic action and optional grounding_hints,
        forwards them to AgentTrek, and reports the result.

        AgentTrek performs:
        - DOM observation
        - Element grounding (using hints as soft guidance)
        - Action execution
        - Success/failure determination

        This adapter only:
        - Packages the action
        - Forwards to AgentTrek
        - Reports result

        Args:
            action_semantic: Semantic action with optional grounding_hints
            env: Web environment (passed to AgentTrek)

        Returns:
            True if AgentTrek executed successfully, False otherwise
        """
        # Normalize semantic to ensure we have description
        semantic_dict = normalize_semantic(action_semantic)
        description = semantic_dict.get("description", "unknown action")
        intent = semantic_dict.get("intent")
        action_object = semantic_dict.get("object")
        context = semantic_dict.get("context")
        grounding_hints = action_semantic.grounding_hints

        logger.info(f"Forwarding to AgentTrek: {description}")
        if intent:
            logger.debug(f"  Intent: {intent}, Object: {action_object}")
        if grounding_hints and not grounding_hints.is_empty():
            logger.debug(f"  Hints: target_role={grounding_hints.target_role}, "
                        f"keywords={grounding_hints.keywords}")

        try:
            # Forward to AgentTrek
            success = await self._execute_via_agenttrek(
                intent=intent or "",
                object=action_object or "",
                context=context,
                description=description,
                grounding_hints=grounding_hints,
                env=env
            )

            if success:
                logger.info(f"AgentTrek executed successfully: {description}")
            else:
                logger.warning(f"AgentTrek execution failed: {description}")

            return success

        except Exception as e:
            logger.error(f"Error forwarding to AgentTrek: {e}", exc_info=True)
            return False

    async def _execute_via_agenttrek(
        self,
        intent: str,
        object: str,
        context: Optional[str],
        description: str,
        grounding_hints,
        env
    ) -> bool:
        """
        Execute action via AgentTrek.

        This is where the actual forwarding happens. AgentTrek receives:
        - Semantic action (intent, object, context)
        - Grounding hints (soft guidance)
        - Environment access (for DOM observation and execution)

        AgentTrek performs:
        1. Gets current DOM observation
        2. Uses LLM to ground semantic action to specific element
        3. Executes the action via environment
        4. Returns success/failure

        Args:
            intent: Action intent
            object: Action object
            context: Optional context
            description: Full description
            grounding_hints: Optional GroundingHints
            env: Environment with browser access

        Returns:
            True if execution succeeded, False otherwise
        """
        try:
            # Step 1: Get current observation
            observation = await env.observe()
            current_url = observation.get('url', '')
            dom_elements = observation.get('dom_elements', [])
            visible_text = observation.get('visible_text', '')[:2000]  # Limit text length

            if not dom_elements:
                logger.warning("No DOM elements available for grounding")
                return False

            logger.debug(f"AgentTrek grounding with {len(dom_elements)} DOM elements")

            # Rank and trim candidates so prompt keeps the most relevant controls.
            candidate_elements = self._prepare_candidate_elements(
                intent=intent,
                object=object,
                grounding_hints=grounding_hints,
                dom_elements=dom_elements,
                limit=60
            )

            if not candidate_elements:
                logger.warning("No candidate DOM elements after ranking")
                return False

            # Step 2: Compile semantic action into explicit instruction
            compiled_instruction = self._compile_action_instruction(
                intent=intent,
                object=object,
                context=context,
                grounding_hints=grounding_hints
            )

            logger.debug(f"Compiled instruction: {compiled_instruction}")

            # Step 3: Build grounding prompt with compiled instruction
            prompt = self._build_grounding_prompt(
                intent=intent,
                object=object,
                context=context,
                compiled_instruction=compiled_instruction,
                grounding_hints=grounding_hints,
                dom_elements=candidate_elements,
                current_url=current_url,
                visible_text=visible_text
            )

            # Step 4: Call LLM for grounding decision
            if not self._client:
                logger.error("OpenAI client not initialized - cannot call AgentTrek LLM")
                return False

            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert web automation agent. Ground semantic actions to specific DOM elements and decide the interaction type."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=500
            )

            llm_output = response.choices[0].message.content
            logger.debug(f"AgentTrek LLM response: {llm_output[:200]}...")

            # Step 5: Parse LLM response to extract action details
            action = self._parse_grounding_response(llm_output, intent, candidate_elements)
            if not action:
                logger.warning("Failed to parse AgentTrek grounding response, trying heuristic fallback")
                action = self._heuristic_ground_action(
                    intent=intent,
                    object=object,
                    grounding_hints=grounding_hints,
                    dom_elements=candidate_elements
                )
                if not action:
                    return False

            logger.info(f"AgentTrek grounded to: {action.type.value} on '{action.target}'")

            # Step 6: Execute action via environment
            observation_after, done = await env.step(action)
            success = observation_after.get('action_success', False)

            if success:
                logger.info(f"AgentTrek execution successful: {description}")
            else:
                logger.warning(f"AgentTrek execution failed: {description}")

            return success

        except Exception as e:
            logger.error(f"Error during AgentTrek execution: {e}", exc_info=True)
            return False

    def _compile_action_instruction(
        self,
        intent: str,
        object: str,
        context: Optional[str],
        grounding_hints
    ) -> str:
        """
        Compile semantic action into explicit natural-language instruction.

        This transforms abstract semantic actions (e.g., "search products") into
        concrete, explicit instructions that mention UI affordances, regions, and
        interaction patterns. This helps AgentTrek avoid falling back to generic
        links or vague elements.

        Args:
            intent: Action intent (e.g., "search", "sign_in", "view")
            object: Action object (e.g., "products", "account", "details")
            context: Optional additional context
            grounding_hints: Optional GroundingHints with target_role, region, keywords

        Returns:
            Explicit natural-language instruction for AgentTrek

        Examples:
            - intent="search", object="products", hints.target_role=["input"]
              → "Type into the search input field to search for products."

            - intent="sign_in", object="account", hints.preferred_region=["header"]
              → "Click the 'Sign In' link or button in the page header."

            - intent="view", object="product details"
              → "Click on a product item or card to view its details."
        """
        # Extract hint information
        target_roles = []
        preferred_regions = []
        keywords = []

        if grounding_hints and not grounding_hints.is_empty():
            target_roles = grounding_hints.target_role or []
            preferred_regions = grounding_hints.preferred_region or []
            keywords = grounding_hints.keywords or []

        # Determine UI affordance from hints or intent
        affordance = self._determine_affordance(intent, target_roles)

        # Determine region
        region_phrase = ""
        if preferred_regions:
            if "header" in preferred_regions:
                region_phrase = "in the page header "
            elif "main_content" in preferred_regions or "main" in preferred_regions:
                region_phrase = "in the main content area "
            elif "sidebar" in preferred_regions:
                region_phrase = "in the sidebar "
            elif "footer" in preferred_regions:
                region_phrase = "in the page footer "

        # Build explicit instruction based on affordance and intent
        if affordance == "input":
            # Typing action
            keyword_phrase = f" for {' '.join(keywords[:3])}" if keywords else ""
            return f"Type into the {object} input field {region_phrase}to {intent}{keyword_phrase}."

        elif affordance == "button":
            # Button click action
            label_hint = f" labeled '{keywords[0]}'" if keywords else ""
            return f"Click the {object} button{label_hint} {region_phrase}to {intent}."

        elif affordance == "dropdown" or affordance == "select":
            # Selection action
            return f"Select an option from the {object} dropdown menu {region_phrase}to {intent}."

        elif affordance == "checkbox":
            # Checkbox toggle
            return f"Toggle the {object} checkbox {region_phrase}to {intent}."

        elif affordance == "link":
            # Link navigation (but only if specifically hinted)
            label_hint = f" labeled '{keywords[0]}'" if keywords else ""
            return f"Click the {object} link{label_hint} {region_phrase}to {intent}."

        else:
            # Generic clickable element (card, item, etc.)
            element_type = target_roles[0] if target_roles else "element"
            return f"Click on a {object} {element_type} {region_phrase}to {intent}."

    def _determine_affordance(
        self,
        intent: str,
        target_roles: List[str]
    ) -> str:
        """
        Determine UI affordance from intent and target roles.

        Args:
            intent: Action intent
            target_roles: List of suggested element roles from hints

        Returns:
            Affordance type: "input", "button", "dropdown", "link", "card", etc.
        """
        # Check explicit roles first
        for role in target_roles:
            role_lower = role.lower()
            if "input" in role_lower or "textbox" in role_lower:
                return "input"
            elif "button" in role_lower or "submit" in role_lower:
                return "button"
            elif "dropdown" in role_lower or "select" in role_lower:
                return "dropdown"
            elif "checkbox" in role_lower:
                return "checkbox"
            elif "link" in role_lower:
                return "link"
            elif "menu" in role_lower:
                return "menu"
            elif "card" in role_lower:
                return "card"

        # Infer from intent if no explicit role
        intent_lower = intent.lower()
        if intent_lower in ["search", "type", "enter", "input"]:
            return "input"
        elif intent_lower in ["submit", "confirm", "send"]:
            return "button"
        elif intent_lower in ["select", "choose", "filter"]:
            return "dropdown"
        elif intent_lower in ["toggle", "enable", "disable"]:
            return "checkbox"
        elif intent_lower in ["navigate", "go_to"]:
            return "link"
        else:
            # Default to generic clickable
            return "clickable"

    def _build_grounding_prompt(
        self,
        intent: str,
        object: str,
        context: Optional[str],
        compiled_instruction: str,
        grounding_hints,
        dom_elements: List[Dict[str, str]],
        current_url: str,
        visible_text: str
    ) -> str:
        """
        Build prompt for LLM to ground semantic action to DOM element.

        Args:
            intent: Action intent
            object: Action object
            context: Optional context
            compiled_instruction: Explicit natural-language instruction
            grounding_hints: Optional GroundingHints
            dom_elements: List of interactive DOM elements with selectors
            current_url: Current page URL
            visible_text: Visible text content

        Returns:
            Formatted prompt string
        """
        # Format DOM elements (limit to top 20 to save tokens)
        elements_text = []
        for i, elem in enumerate(dom_elements[:20], 1):
            selector = elem.get('selector', '')
            text = elem.get('text', '')
            elem_type = elem.get('type', 'element')
            elements_text.append(f"{i}. {elem_type}: '{text}' [selector: {selector}]")

        elements_str = "\n".join(elements_text)

        # Build hints section if available
        hints_section = ""
        if grounding_hints and not grounding_hints.is_empty():
            hints_parts = []
            if grounding_hints.keywords:
                hints_parts.append(f"  - Keywords to look for: {', '.join(grounding_hints.keywords)}")
            if grounding_hints.exclude_keywords:
                hints_parts.append(f"  - Keywords to avoid: {', '.join(grounding_hints.exclude_keywords)}")
            if grounding_hints.target_role:
                hints_parts.append(f"  - Suggested element role: {', '.join(grounding_hints.target_role)}")
            if grounding_hints.element_affordance:
                hints_parts.append(f"  - Suggested interactions: {', '.join(grounding_hints.element_affordance)}")
            if grounding_hints.preferred_region:
                hints_parts.append(f"  - Preferred regions: {', '.join(grounding_hints.preferred_region)}")

            if hints_parts:
                hints_section = "\n\nGrounding Hints (soft guidance, not mandatory):\n" + "\n".join(hints_parts)

        prompt = f"""You are a web automation agent. Ground the following action to a specific DOM element and determine the interaction type.

Current URL: {current_url}

Action Instruction:
{compiled_instruction}

Semantic Details:
- Intent: {intent}
- Object: {object}
- Context: {context or 'none'}{hints_section}

Available DOM Elements:
{elements_str}

Visible Text Excerpt:
{visible_text}

Your task:
1. Identify which DOM element best matches the semantic action
2. Determine the interaction type (CLICK, TYPE, NAVIGATE, etc.)
3. If TYPE action, provide the text to type

Respond with ONLY valid JSON in this format:
{{
  "element_index": <number from 1-{min(20, len(dom_elements))}, or 0 if navigation>,
  "action_type": "CLICK|TYPE|NAVIGATE",
  "type_value": "<text to type, only if action_type is TYPE>",
  "reasoning": "<brief explanation>"
}}

If this is a navigation action (e.g., "go to", "visit"), use action_type "NAVIGATE" with element_index 0.
"""

        return prompt

    def _prepare_candidate_elements(
        self,
        intent: str,
        object: str,
        grounding_hints,
        dom_elements: List[Dict[str, str]],
        limit: int = 60
    ) -> List[Dict[str, str]]:
        """Score and rank DOM elements so the LLM sees the most relevant candidates first."""
        intent_l = (intent or "").lower()
        object_l = (object or "").lower()
        keywords = []
        exclude_keywords = []

        if grounding_hints and not grounding_hints.is_empty():
            keywords = [k.lower() for k in (grounding_hints.keywords or []) if k]
            exclude_keywords = [k.lower() for k in (grounding_hints.exclude_keywords or []) if k]

        object_tokens = [t for t in re.split(r"\W+", object_l) if len(t) > 2]

        scored: List[tuple[float, Dict[str, str]]] = []
        for elem in dom_elements:
            text = (elem.get("text") or "").strip().lower()
            selector = (elem.get("selector") or "").strip().lower()
            elem_type = (elem.get("type") or "").strip().lower()

            score = 0.0

            if "search" in intent_l or "type" in intent_l or "input" in intent_l:
                if any(k in selector for k in ["input", "textarea", "search", "q", "query"]):
                    score += 3.0
                if elem_type in ["input", "textarea"]:
                    score += 2.0

            if any(k in intent_l for k in ["add", "buy", "cart", "checkout"]):
                if "add to cart" in text:
                    score += 3.0
                if "cart" in text:
                    score += 1.5

            for kw in keywords:
                if kw in text:
                    score += 1.5
                if kw in selector:
                    score += 0.8

            for tok in object_tokens:
                if tok in text:
                    score += 0.7

            for ex_kw in exclude_keywords:
                if ex_kw in text:
                    score -= 3.0

            if selector.startswith("#"):
                score += 0.8

            scored.append((score, elem))

        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = [elem for _, elem in scored[:limit]]
        return candidates

    def _parse_grounding_response(
        self,
        llm_output: str,
        intent: str,
        dom_elements: List[Dict[str, str]]
    ) -> Optional[Action]:
        """
        Parse LLM grounding response into Action object.

        Args:
            llm_output: Raw LLM response text
            intent: Original semantic intent (for fallback)
            dom_elements: List of DOM elements (for selector lookup)

        Returns:
            Action object or None if parsing fails
        """
        try:
            data = self._extract_grounding_json(llm_output)
            if not data:
                logger.warning("No parseable JSON found in LLM response")
                return None

            element_index = data.get('element_index', 0)
            action_type_str = data.get('action_type', 'CLICK').upper()
            type_value = data.get('type_value', '')
            reasoning = data.get('reasoning', '')

            logger.debug(f"Grounding reasoning: {reasoning}")

            # Map to ActionType
            action_type_map = {
                'CLICK': ActionType.CLICK,
                'TYPE': ActionType.TYPE,
                'NAVIGATE': ActionType.NAVIGATE,
                'SCROLL': ActionType.SCROLL,
                'SELECT': ActionType.SELECT,
                'WAIT': ActionType.WAIT
            }

            action_type = action_type_map.get(action_type_str, ActionType.CLICK)

            # Determine target
            if action_type == ActionType.NAVIGATE or element_index == 0:
                # Navigation action - target is URL or intent-based
                target = type_value if type_value else ""
            else:
                # Element-based action - retrieve selector from dom_elements
                # Note: element_index is 1-based in prompt
                actual_index = element_index - 1
                if 0 <= actual_index < len(dom_elements):
                    element = dom_elements[actual_index]
                    target = self._build_target_for_element(element, action_type)
                    if not target:
                        logger.warning(f"Element {element_index} has no selector")
                        return None
                else:
                    logger.warning(f"Element index {element_index} out of range (1-{len(dom_elements)})")
                    return None

            # Create Action
            value = type_value if action_type == ActionType.TYPE else None

            return Action(
                type=action_type,
                target=target,
                value=value
            )

        except Exception as e:
            logger.error(f"Error parsing grounding response: {e}")
            return None

    def _extract_grounding_json(self, llm_output: str) -> Optional[Dict[str, Any]]:
        """Extract first valid JSON object from model output."""
        text = (llm_output or "").strip()
        if not text:
            return None

        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    snippet = text[start:i + 1]
                    try:
                        return json.loads(snippet)
                    except Exception:
                        return None
        return None

    def _build_target_for_element(self, element: Dict[str, str], action_type: ActionType) -> str:
        """Build a robust Playwright target from element info."""
        selector = (element.get("selector") or "").strip()
        text = (element.get("text") or "").strip()

        if action_type == ActionType.TYPE:
            if selector and any(k in selector.lower() for k in ["input", "textarea", "search"]):
                return selector
            return "input[type='search'], input[type='text'], textarea"

        if selector.startswith("#"):
            return selector

        if text:
            return f"text={text}"

        return selector

    def _heuristic_ground_action(
        self,
        intent: str,
        object: str,
        grounding_hints,
        dom_elements: List[Dict[str, str]]
    ) -> Optional[Action]:
        """Fallback grounding policy when LLM output is unusable."""
        intent_l = (intent or "").lower()
        object_l = (object or "").lower()
        keywords = []
        if grounding_hints and not grounding_hints.is_empty():
            keywords = [k.lower() for k in (grounding_hints.keywords or []) if k]

        # TYPE-like intents
        if any(k in intent_l for k in ["search", "type", "input", "enter"]):
            return Action(
                type=ActionType.TYPE,
                target="input[type='search'], input[type='text'], textarea",
                value=(object or "test")
            )

        # CLICK-like intents
        best = None
        best_score = -1.0
        for elem in dom_elements:
            text = (elem.get("text") or "").lower()
            selector = (elem.get("selector") or "").lower()
            score = 0.0

            for kw in keywords:
                if kw in text:
                    score += 2.0
            for tok in re.split(r"\W+", object_l):
                if len(tok) > 2 and tok in text:
                    score += 0.8
            if any(k in intent_l for k in ["cart", "add", "buy", "checkout"]) and "cart" in text:
                score += 1.5
            if selector.startswith("#"):
                score += 0.5

            if score > best_score:
                best_score = score
                best = elem

        if best:
            return Action(type=ActionType.CLICK, target=self._build_target_for_element(best, ActionType.CLICK))

        return Action(type=ActionType.CLICK, target="text=Add to Cart")


# ============================================================================
# Factory Function
# ============================================================================

def create_agenttrek_adapter(
    model_name: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: Optional[float] = None
) -> AgentTrekExplorationAdapter:
    """
    Factory function to create AgentTrek exploration adapter.

    Loads configuration from .env if parameters not provided.

    Args:
        model_name: HuggingFace model name
        base_url: API base URL
        api_key: API key
        temperature: LLM temperature

    Returns:
        AgentTrekExplorationAdapter instance
    """
    return AgentTrekExplorationAdapter(
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature or env.get_float("EXPLORER_TEMPERATURE", 0.2)
    )
