"""
Screen deduplication logic for exploration.

Determines when two screens are semantically equivalent
to avoid redundant exploration.
"""

import logging
from typing import Dict, Optional
from difflib import SequenceMatcher

from exploration.schema import Screen

logger = logging.getLogger(__name__)


class ScreenDeduplicator:
    """
    Deduplicates screens based on multiple signals:
    - URL pattern
    - Semantic summary similarity
    - DOM fingerprint
    """
    
    def __init__(
        self,
        url_weight: float = 0.4,
        semantic_weight: float = 0.4,
        dom_weight: float = 0.2,
        similarity_threshold: float = 0.85
    ):
        """
        Initialize deduplicator.
        
        Args:
            url_weight: Weight for URL pattern similarity
            semantic_weight: Weight for semantic summary similarity
            dom_weight: Weight for DOM fingerprint similarity
            similarity_threshold: Threshold for considering screens duplicate
        """
        self.url_weight = url_weight
        self.semantic_weight = semantic_weight
        self.dom_weight = dom_weight
        self.similarity_threshold = similarity_threshold
        
        # Cache of known screens
        self.known_screens: Dict[str, Screen] = {}
        
        # Mapping of duplicate screen_ids to canonical screen_id
        self.canonical_mapping: Dict[str, str] = {}
    
    def add_screen(self, screen: Screen, previous_screen: Optional[Screen] = None) -> tuple[str, bool]:
        """
        Add a screen to the deduplicator.
        
        If the screen is similar to an existing screen, returns the
        canonical screen_id. Otherwise, adds as new screen.
        
        Special case: Validation screens (error states) are always treated
        as new screens to preserve fail-repair trajectories.
        
        Args:
            screen: Screen to add
            previous_screen: Previous screen (for validation detection)
            
        Returns:
            Tuple of (canonical_screen_id, is_new)
            - canonical_screen_id: ID of the canonical screen
            - is_new: True if this is a new unique screen
        """
        # Check if already seen this exact screen
        if screen.screen_id in self.canonical_mapping:
            canonical_id = self.canonical_mapping[screen.screen_id]
            return canonical_id, False
        
        # Check for validation screen (fail-repair scenario)
        if previous_screen and self.is_validation_screen(previous_screen, screen):
            # Force this as a new screen to preserve fail-repair trajectory
            self.known_screens[screen.screen_id] = screen
            self.canonical_mapping[screen.screen_id] = screen.screen_id
            logger.info(f"Screen {screen.screen_id} detected as validation screen (preserved)")
            return screen.screen_id, True
        
        # Find most similar existing screen
        best_match, best_similarity = self._find_most_similar(screen)
        
        if best_match is not None and best_similarity >= self.similarity_threshold:
            # This is a duplicate
            canonical_id = best_match.screen_id
            self.canonical_mapping[screen.screen_id] = canonical_id
            logger.debug(f"Screen {screen.screen_id} is duplicate of {canonical_id} (similarity: {best_similarity:.2f})")
            return canonical_id, False
        else:
            # This is a new unique screen
            self.known_screens[screen.screen_id] = screen
            self.canonical_mapping[screen.screen_id] = screen.screen_id
            logger.debug(f"Screen {screen.screen_id} is new (best similarity: {best_similarity:.2f})")
            return screen.screen_id, True
    
    def get_canonical_id(self, screen_id: str) -> str:
        """
        Get the canonical screen_id for a given screen_id.
        
        Args:
            screen_id: Screen ID (possibly duplicate)
            
        Returns:
            Canonical screen ID
        """
        return self.canonical_mapping.get(screen_id, screen_id)
    
    def _find_most_similar(self, screen: Screen) -> tuple[Optional[Screen], float]:
        """
        Find the most similar existing screen.
        
        Args:
            screen: Screen to compare
            
        Returns:
            Tuple of (most_similar_screen, similarity_score)
        """
        if not self.known_screens:
            return None, 0.0
        
        best_match = None
        best_similarity = 0.0
        
        for existing_screen in self.known_screens.values():
            similarity = self._compute_similarity(screen, existing_screen)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = existing_screen
        
        return best_match, best_similarity
    
    def _compute_similarity(self, screen1: Screen, screen2: Screen) -> float:
        """
        Compute similarity between two screens.
        
        Uses weighted combination of:
        - URL pattern similarity
        - Semantic summary similarity
        - DOM fingerprint similarity
        
        Args:
            screen1: First screen
            screen2: Second screen
            
        Returns:
            Similarity score between 0 and 1
        """
        # URL pattern similarity
        url_sim = self._url_similarity(screen1, screen2)
        
        # Semantic summary similarity
        semantic_sim = self._text_similarity(screen1.semantic_summary, screen2.semantic_summary)
        
        # DOM fingerprint similarity
        dom_sim = self._fingerprint_similarity(screen1.dom_fingerprint, screen2.dom_fingerprint)
        
        # Weighted combination
        total_similarity = (
            self.url_weight * url_sim +
            self.semantic_weight * semantic_sim +
            self.dom_weight * dom_sim
        )
        
        return total_similarity
    
    def _url_similarity(self, screen1: Screen, screen2: Screen) -> float:
        """
        Compute URL pattern similarity.
        
        Args:
            screen1: First screen
            screen2: Second screen
            
        Returns:
            Similarity score between 0 and 1
        """
        # Extract URL patterns
        pattern1 = screen1._extract_url_pattern()
        pattern2 = screen2._extract_url_pattern()
        
        if pattern1 == pattern2:
            return 1.0
        
        # Use string similarity as fallback
        return self._text_similarity(pattern1, pattern2)
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Compute text similarity using sequence matching.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0
        
        # Use SequenceMatcher for string similarity
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()
    
    def _fingerprint_similarity(self, fp1: Optional[str], fp2: Optional[str]) -> float:
        """
        Compute fingerprint similarity.
        
        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            
        Returns:
            Similarity score between 0 and 1
        """
        if not fp1 or not fp2:
            return 0.0
        
        # Fingerprints are structured as: url_pattern::dom_hash::text_hash
        parts1 = fp1.split("::")
        parts2 = fp2.split("::")
        
        if len(parts1) != 3 or len(parts2) != 3:
            return 0.0
        
        # Compare each component
        url_match = 1.0 if parts1[0] == parts2[0] else 0.0
        dom_match = 1.0 if parts1[1] == parts2[1] else 0.0
        text_match = 1.0 if parts1[2] == parts2[2] else 0.0
        
        # Average the components
        return (url_match + dom_match + text_match) / 3.0
    
    def is_validation_screen(self, previous_screen: Screen, current_screen: Screen) -> bool:
        """
        Detect if current screen is a validation/error state.
        
        Validation screens occur after form submission failures and contain:
        - Same or very similar URL (didn't navigate away)
        - DOM or visible text changed (error messages appeared)
        - Validation-related keywords
        
        Args:
            previous_screen: Screen before action
            current_screen: Screen after action
            
        Returns:
            True if current screen is a validation screen
        """
        # Check 1: URL should be same or very similar (didn't navigate)
        url_sim = self._url_similarity(previous_screen, current_screen)
        if url_sim < 0.8:  # Navigated to different page
            return False
        
        # Check 2: DOM or text must have changed (error appeared)
        # If fingerprints are identical, it's exact same screen
        if previous_screen.dom_fingerprint == current_screen.dom_fingerprint:
            return False
        
        # Check 3: Look for validation keywords in visible text or semantic summary
        validation_keywords = [
            'required', 'please select', 'invalid', 'error', 'must',
            'missing', 'cannot be blank', 'cannot be empty', 'field is required',
            'please enter', 'please fill', 'validation failed', 'please provide',
            'is required', 'are required', 'cannot proceed', 'incomplete'
        ]
        
        combined_text = (
            current_screen.visible_text.lower() + ' ' + 
            current_screen.semantic_summary.lower()
        )
        
        has_validation_keyword = any(
            keyword in combined_text 
            for keyword in validation_keywords
        )
        
        if has_validation_keyword:
            logger.debug(
                f"Validation screen detected: URL similar ({url_sim:.2f}), "
                f"DOM changed, validation keywords found"
            )
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get deduplication statistics.
        
        Returns:
            Dict with stats
        """
        unique_screens = len(self.known_screens)
        total_screens = len(self.canonical_mapping)
        duplicates = total_screens - unique_screens
        
        return {
            "unique_screens": unique_screens,
            "total_screens_seen": total_screens,
            "duplicates_found": duplicates
        }
