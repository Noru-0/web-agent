"""
Screen analyzer - LLM-based screen understanding.

Analyzes web screens to extract:
1. Semantic summary
2. Screen type classification
3. Possible action affordances
"""

import json
import os
import re
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from exploration.schema import Screen, ActionSemantic, ScreenType
from exploration.semantic_normalization import normalize_semantic

logger = logging.getLogger(__name__)


class ScreenAnalyzer:
    """
    Analyzes web screens using LLM to extract semantic information.

    This is the main interface for screen understanding during exploration.
    """

    def __init__(self, llm_client=None, prompt_path: Optional[Path] = None):
        """
        Initialize screen analyzer.

        Args:
            llm_client: LLM client (e.g., OpenAI, Anthropic). If None, uses default from .env
            prompt_path: Path to prompt template file
        """
        self.llm_client = llm_client

        # Load prompt template
        if prompt_path is None:
            prompt_path = Path(__file__).parent.parent.parent / "training" / "prompts" / "web_explore.txt"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

    def analyze_screen(
        self,
        url: str,
        dom_snapshot: str,
        visible_text: str,
        screenshot: Optional[str] = None
    ) -> tuple[str, ScreenType, List[ActionSemantic]]:
        """
        Analyze a screen and extract semantic information.

        Args:
            url: Current page URL
            dom_snapshot: Cleaned HTML
            visible_text: Extracted visible text
            screenshot: Optional screenshot (base64 or path)

        Returns:
            Tuple of (semantic_summary, screen_type, action_semantics)
        """
        # Create DOM summary (truncate if too long)
        dom_summary = self._create_dom_summary(dom_snapshot)

        # Build prompt
        prompt = self.prompt_template.format(
            url=url,
            visible_text=visible_text[:2000],  # Truncate to avoid token limits
            dom_summary=dom_summary
        )

        # Call LLM
        response = self._call_llm(prompt, screenshot=screenshot)

        # DEBUG: Log raw response to check if hints are present
        logger.info(f"Raw LLM response (first 800 chars): {response[:800]}")

        # Parse and validate response
        result = self._parse_llm_response(response)

        # Convert to objects
        semantic_summary = result["screen_summary"]

        # Infer screen type from summary (no longer provided by LLM)
        screen_type = self._infer_screen_type(semantic_summary, visible_text)

        # Parse semantic actions (flexible - handles both structured and free-text)
        action_semantics = self._parse_action_semantics(result["semantic_actions"])

        return semantic_summary, screen_type, action_semantics

    def _parse_action_semantics(self, actions_data: list) -> List[ActionSemantic]:
        """
        Parse action semantics from LLM response (flexible format).

        Handles:
        - Structured with grounding_hints: {"intent": "search", "object": "items", "grounding_hints": {...}}
        - Structured without hints: {"intent": "search", "object": "items", ...}
        - Free-text: "click login button"
        - Mixed formats

        Args:
            actions_data: List of actions from LLM (any format)

        Returns:
            List of ActionSemantic objects with optional grounding_hints
        """
        from exploration.schema import GroundingHints

        action_semantics = []

        for action_data in actions_data:
            try:
                # Normalize to dict
                normalized = normalize_semantic(action_data)

                # Extract grounding_hints if present
                hints = None
                if isinstance(action_data, dict) and 'grounding_hints' in action_data:
                    hints_data = action_data['grounding_hints']
                    if hints_data and isinstance(hints_data, dict):
                        try:
                            hints = GroundingHints.from_dict(hints_data)
                            logger.debug(f"Parsed grounding_hints for action: {hints}")
                        except Exception as e:
                            logger.warning(f"Failed to parse grounding_hints: {e}, using None")
                            hints = None

                # Create ActionSemantic from normalized dict
                action_sem = ActionSemantic(
                    intent=normalized.get("intent"),
                    object=normalized.get("object"),
                    context=normalized.get("context"),
                    description=normalized.get("description"),  # Use LLM description if provided
                    grounding_hints=hints,  # Include parsed hints
                    confidence=normalized.get("confidence", 0.75)
                )
                action_semantics.append(action_sem)

            except Exception as e:
                logger.error(f"Error parsing action semantic: {e}, data={action_data}")
                # Fallback: Create from string
                if isinstance(action_data, str):
                    action_semantics.append(ActionSemantic.from_string(action_data, confidence=0.5))
                else:
                    logger.warning(f"Skipping unparseable action: {action_data}")

        return action_semantics

    def _create_dom_summary(self, dom_snapshot: str, max_length: int = 1500) -> str:
        """
        Create a concise DOM summary for the LLM.

        Args:
            dom_snapshot: Full DOM HTML
            max_length: Maximum character length

        Returns:
            Truncated DOM summary
        """
        # Extract key structural elements
        import re

        # Find important tags
        important_tags = r'<(button|a|input|form|select|textarea|nav|header|footer|main)[^>]*>'
        elements = re.findall(important_tags, dom_snapshot, re.IGNORECASE)

        # Count element types
        from collections import Counter
        element_counts = Counter(elements)

        summary = f"DOM Structure:\n"
        for tag, count in element_counts.most_common(10):
            summary += f"  {tag}: {count}\n"

        # Also include a sample of the DOM
        summary += f"\nDOM Sample:\n{dom_snapshot[:max_length]}..."

        return summary

    def _call_llm(self, prompt: str, screenshot: Optional[str] = None) -> str:
        """
        Call LLM with the prompt.

        Args:
            prompt: Formatted prompt

        Returns:
            LLM response text
        """
        if self.llm_client is None:
            # Use provider from config
            from utils.env import env
            provider = env.get("LLM_PROVIDER", "openai").lower()

            if provider == "llama":
                return self._call_llama(prompt, screenshot=screenshot)
            elif provider == "openai":
                return self._call_openai(prompt, screenshot=screenshot)
            else:
                logger.warning(f"Unknown LLM provider: {provider}, defaulting to OpenAI")
                return self._call_openai(prompt, screenshot=screenshot)
        else:
            # Use provided client
            return self.llm_client(prompt)

    def _call_openai(self, prompt: str, screenshot: Optional[str] = None) -> str:
        """
        Call OpenAI API.

        Args:
            prompt: Formatted prompt

        Returns:
            Response text
        """
        try:
            import openai
            from utils.env import env

            # Get API key and model from .env or environment
            api_key = env.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set. Add to .env file or environment.")

            # Allow configuring OpenAI model via .env
            model = env.get("OPENAI_MODEL") or env.get("LLM_MODEL", "gpt-4o-mini")
            temperature = float(env.get_float("LLM_TEMPERATURE", 0.3))
            max_tokens = int(env.get_int("LLM_MAX_TOKENS", 2048))

            client = openai.OpenAI(api_key=api_key)

            messages = [
                {"role": "system", "content": "You are a web UI analyzer. Always respond with valid JSON."}
            ]

            image_data_url = self._normalize_screenshot_data_url(screenshot)
            if image_data_url:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}}
                    ]
                })
            else:
                messages.append({"role": "user", "content": prompt})

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )
            except Exception as e:
                if image_data_url:
                    logger.warning(f"OpenAI multimodal call failed, retrying text-only: {e}")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a web UI analyzer. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"}
                    )
                else:
                    raise

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            # Return fallback response
            return self._get_fallback_response()

    def _call_llama(self, prompt: str, screenshot: Optional[str] = None) -> str:
        """
        Call Llama model via HuggingFace Router API.

        Uses the new router endpoint (api-inference.huggingface.co is deprecated).

        Args:
            prompt: Formatted prompt

        Returns:
            Response text
        """
        try:
            import openai  # Use openai library for HuggingFace Router (OpenAI-compatible)
            from utils.env import env

            # Get configuration from environment
            api_token = env.get("HUGGINGFACEHUB_API_TOKEN") or env.get("HUGGINGFACE_API_KEY") or env.get("LLM_API_KEY")
            model = env.get("HF_MODEL") or env.get("LLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
            api_base = env.get("HF_API_BASE", "https://router.huggingface.co")
            temperature = float(env.get_float("LLM_TEMPERATURE", 0.2))
            max_tokens = int(env.get_int("LLM_MAX_TOKENS", 2048))

            if not api_token:
                raise ValueError("HUGGINGFACEHUB_API_TOKEN not set. Add to .env file or environment.")

            # Use OpenAI library with HuggingFace Router (OpenAI-compatible)
            client = openai.OpenAI(
                base_url=f"{api_base}/v1",
                api_key=api_token
            )

            logger.info(f"Calling HuggingFace router with model: {model}")

            # Build messages. Attach screenshot if provider/model supports it.
            messages = [
                {"role": "system", "content": "You are a web UI analyzer. Always respond with valid JSON."}
            ]

            image_data_url = self._normalize_screenshot_data_url(screenshot)
            if image_data_url:
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}}
                    ]
                })
            else:
                messages.append({"role": "user", "content": prompt})

            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            except Exception as e:
                if image_data_url:
                    logger.warning(f"Llama multimodal call failed, retrying text-only: {e}")
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are a web UI analyzer. Always respond with valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=max_tokens,
                        temperature=temperature
                    )
                else:
                    raise

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error calling HuggingFace Llama API: {e}")
            # Return fallback response (fail-soft behavior)
            return self._get_fallback_response()

    def _get_fallback_response(self) -> str:
        """
        Return a fallback response when LLM call fails.

        Returns:
            JSON string with minimal analysis
        """
        return json.dumps({
            "screen_summary": "Web page (analysis unavailable)",
            "semantic_actions": []
        })

    def _normalize_screenshot_data_url(self, screenshot: Optional[str]) -> Optional[str]:
        """
        Normalize screenshot input to a data URL usable by multimodal APIs.

        Accepts:
        - Full data URL (data:image/...;base64,...)
        - Raw base64 image bytes
        - Local file path
        """
        if not screenshot:
            return None

        if screenshot.startswith("data:image"):
            return screenshot

        if os.path.exists(screenshot):
            try:
                with open(screenshot, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("ascii")
                return f"data:image/png;base64,{encoded}"
            except Exception as e:
                logger.warning(f"Failed to read screenshot path '{screenshot}': {e}")
                return None

        # Assume screenshot is raw base64 content.
        return f"data:image/jpeg;base64,{screenshot}"

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate LLM response with structured semantic actions.

        Args:
            response: Raw LLM response

        Returns:
            Validated dict with screen_summary and semantic_actions
        """
        try:
            # Extract clean JSON from response (handles markdown fences and extra text)
            clean_json = self._extract_json_from_response(response)

            # Parse JSON
            result = json.loads(clean_json)

            # Validate required fields
            if "screen_summary" not in result:
                raise ValueError("Missing screen_summary")
            if "semantic_actions" not in result:
                raise ValueError("Missing semantic_actions")

            # Validate semantic_actions is a list
            if not isinstance(result["semantic_actions"], list):
                result["semantic_actions"] = []

            # Validate each action structure
            validated_actions = []
            for action in result["semantic_actions"]:
                if not isinstance(action, dict):
                    logger.warning(f"Skipping non-dict action: {action}")
                    continue

                # Required fields
                if "intent" not in action or "object" not in action:
                    logger.warning(f"Skipping action missing intent/object: {action}")
                    continue

                # Validate confidence
                confidence = action.get("confidence", 0.75)
                if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
                    logger.warning(f"Invalid confidence {confidence}, defaulting to 0.75")
                    confidence = 0.75

                validated_action = {
                    "intent": str(action["intent"]),
                    "object": str(action["object"]),
                    "context": action.get("context"),
                    "description": action.get("description"),  # NEW: Preserve LLM description
                    "confidence": float(confidence)
                }

                # Preserve grounding_hints if present
                if "grounding_hints" in action:
                    validated_action["grounding_hints"] = action["grounding_hints"]

                validated_actions.append(validated_action)

            result["semantic_actions"] = validated_actions
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Raw response (first 1000 chars): {response[:1000]}")

            # Try to repair JSON
            repaired = self._try_repair_json(response)
            if repaired:
                logger.info("Successfully repaired JSON response")
                return repaired

            return {
                "screen_summary": "Parse error",
                "semantic_actions": []
            }

        except Exception as e:
            logger.error(f"Error validating LLM response: {e}")
            return {
                "screen_summary": "Validation error",
                "semantic_actions": []
            }

    def _extract_json_from_response(self, text: str) -> str:
        """
        Extract clean JSON from LLM response.

        Handles common issues with large LLM models:
        - Markdown code fences (```json ... ```)
        - Extra explanation text before/after JSON
        - Leading/trailing whitespace
        - Arbitrarily nested JSON structures

        Args:
            text: Raw LLM response

        Returns:
            Cleaned JSON string ready for json.loads()

        Raises:
            ValueError: If no valid JSON object found
        """
        # Strip whitespace
        text = text.strip()

        # Remove markdown code fences if present
        # Pattern: ```json\n{...}\n``` or ```\n{...}\n```
        if text.startswith('```'):
            lines = text.split('\n')
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's closing fence
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines).strip()

        # Find first '{' to start JSON extraction
        start_idx = text.find('{')

        if start_idx == -1:
            logger.error("No JSON object found in response")
            logger.error(f"Response preview: {text[:200]}...")
            raise ValueError("No JSON object found in LLM response")

        # Use brace counting to find complete JSON object (handles arbitrary nesting)
        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start_idx, len(text)):
            char = text[i]

            # Handle string escaping
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            # Track string boundaries
            if char == '"':
                in_string = not in_string
                continue

            # Only count braces outside of strings
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found complete JSON object
                        return text[start_idx:i+1]

        # If we get here, braces don't match properly
        logger.warning("Unclosed JSON braces, attempting to extract partial JSON")
        return text[start_idx:]

    def _try_repair_json(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to repair malformed JSON response.

        Common issues:
        - Unterminated strings (LLM output truncated)
        - Trailing commas
        - Unescaped quotes in strings
        - Missing quotes in arrays: ["word, "word2"] → ["word", "word2"]

        Args:
            response: Raw LLM response

        Returns:
            Parsed dict if repair successful, None otherwise
        """
        try:
            # Try 1: Fix common array quote errors: ["word, "next"] → ["word", "next"]
            import re
            # Pattern: matches strings like ["word, " that should be ["word", "
            fixed = re.sub(r'\["([^"]*),\s+"', r'["\1", "', response)
            fixed = re.sub(r'",\s+([^"\s]+),\s+"', r'", "\1", "', fixed)

            try:
                result = json.loads(fixed)
                if "screen_summary" in result and "semantic_actions" in result:
                    logger.info("JSON repair successful (quote fix)")
                    return result
            except:
                pass

            # Try 2: Remove trailing incomplete JSON
            # Find last complete closing brace
            last_brace = response.rfind('}')
            if last_brace > 0:
                truncated = response[:last_brace + 1]
                try:
                    result = json.loads(truncated)
                    if "screen_summary" in result and "semantic_actions" in result:
                        logger.info("JSON repair successful (truncation)")
                        return result
                except:
                    pass

            # Try 3: Add closing braces if missing
            open_braces = response.count('{')
            close_braces = response.count('}')
            if open_braces > close_braces:
                repaired = response + ('}' * (open_braces - close_braces))
                try:
                    result = json.loads(repaired)
                    if "screen_summary" in result and "semantic_actions" in result:
                        logger.info("JSON repair successful (add braces)")
                        return result
                except:
                    pass

            # Try 4: Fix unterminated strings
            # Close any open string quotes
            if response.count('"') % 2 != 0:
                repaired = response + '"}'
                try:
                    result = json.loads(repaired)
                    if "screen_summary" in result and "semantic_actions" in result:
                        logger.info("JSON repair successful (string termination)")
                        return result
                except:
                    pass

            return None

        except Exception as e:
            logger.debug(f"JSON repair failed: {e}")
            return None

    def _infer_screen_type(self, summary: str, visible_text: str) -> ScreenType:
        """
        Infer screen type from summary and visible text.

        This is a heuristic fallback since we no longer ask LLM for screen_type.

        Args:
            summary: Semantic summary of the screen
            visible_text: Visible text content

        Returns:
            Inferred ScreenType
        """
        # Simple keyword-based inference
        # Check more specific types first before generic ones
        text_lower = (summary + " " + visible_text).lower()

        # E-commerce home pages often have "sign in" links but are not login pages
        if any(kw in text_lower for kw in ["home page", "homepage", "welcome", "shop", "e-commerce", "ecommerce"]):
            return ScreenType.HOMEPAGE
        elif any(kw in text_lower for kw in ["checkout", "payment", "billing"]):
            return ScreenType.CHECKOUT
        elif any(kw in text_lower for kw in ["cart", "basket", "shopping bag"]):
            return ScreenType.CART
        elif any(kw in text_lower for kw in ["product detail", "item detail", "product page"]):
            return ScreenType.PRODUCT_DETAIL
        elif any(kw in text_lower for kw in ["product list", "catalog", "results", "products"]):
            return ScreenType.LISTING
        elif any(kw in text_lower for kw in ["article", "blog", "post", "news"]):
            return ScreenType.ARTICLE
        elif any(kw in text_lower for kw in ["login page", "sign in page", "authentication"]):
            return ScreenType.LOGIN
        elif any(kw in text_lower for kw in ["search", "query", "find"]):
            return ScreenType.SEARCH
        elif any(kw in text_lower for kw in ["form", "register", "contact us"]):
            return ScreenType.FORM
        elif any(kw in text_lower for kw in ["menu", "navigation", "nav"]):
            return ScreenType.NAVIGATION
        else:
            return ScreenType.OTHER


def extract_visible_text(html: str) -> str:
    """
    Extract visible text from HTML.

    Utility function for preprocessing HTML before analysis.

    Args:
        html: HTML content

    Returns:
        Visible text
    """
    from bs4 import BeautifulSoup

    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        return text

    except Exception as e:
        logger.error(f"Error extracting visible text: {e}")
        return ""
