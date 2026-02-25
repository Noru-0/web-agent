"""
Unit tests for Task Synthesis functionality.

Tests the TaskSynthesizer class to ensure:
- Action collection works correctly
- Action normalization deduplicates properly
- Task grouping follows patterns
- Confidence computation is accurate
- Priority classification is correct
- Edge cases are handled
"""

import unittest
from exploration import (
    Screen,
    ActionSemantic,
    ScreenType,
    TaskSynthesizer,
    TaskPriority,
    Task,
    TaskGraph
)


class TestTaskSynthesis(unittest.TestCase):
    """Test cases for TaskSynthesizer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.synthesizer = TaskSynthesizer(domain="ecommerce")  # Use explicit domain for consistent tests
    
    def test_empty_screens(self):
        """Test with no screens"""
        screens = []
        task_graph = self.synthesizer.synthesize(screens)
        
        self.assertIsInstance(task_graph, TaskGraph)
        self.assertEqual(len(task_graph.tasks), 0)
        self.assertEqual(task_graph.meta['total_screens'], 0)
    
    def test_screens_with_no_actions(self):
        """Test with screens that have no actions"""
        screen = Screen(
            screen_id="s1",
            url="https://example.com",
            dom_snapshot="",
            visible_text="Empty screen",
            semantic_summary="Empty",
            screen_type=ScreenType.OTHER,
            timestamp="2026-02-24"
        )
        screen.actions = []
        
        task_graph = self.synthesizer.synthesize([screen])
        
        self.assertEqual(len(task_graph.tasks), 0)
    
    def test_single_action(self):
        """Test with a single action"""
        screen = Screen(
            screen_id="s1",
            url="https://example.com",
            dom_snapshot="",
            visible_text="Search page",
            semantic_summary="Search",
            screen_type=ScreenType.SEARCH,
            timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(
                intent="search",
                object="products",
                confidence=0.9,
                action_id="a1"
            )
        ]
        
        task_graph = self.synthesizer.synthesize([screen])
        
        self.assertGreater(len(task_graph.tasks), 0)
        # Should create a "search products" task
        search_tasks = [t for t in task_graph.tasks if "search" in t.name.lower()]
        self.assertEqual(len(search_tasks), 1)
        self.assertEqual(search_tasks[0].priority, TaskPriority.INITIAL)
    
    def test_action_normalization(self):
        """Test that duplicate actions are normalized"""
        screen1 = Screen(
            screen_id="s1",
            url="https://example.com",
            dom_snapshot="",
            visible_text="",
            semantic_summary="",
            screen_type=ScreenType.HOMEPAGE,
            timestamp="2026-02-24"
        )
        screen1.actions = [
            ActionSemantic(intent="search", object="products", confidence=0.9, action_id="a1"),
            ActionSemantic(intent="search", object="products", confidence=0.8, action_id="a2"),
        ]
        
        screen2 = Screen(
            screen_id="s2",
            url="https://example.com/page2",
            dom_snapshot="",
            visible_text="",
            semantic_summary="",
            screen_type=ScreenType.SEARCH,
            timestamp="2026-02-24"
        )
        screen2.actions = [
            ActionSemantic(intent="search", object="products", confidence=0.85, action_id="a3"),
        ]
        
        task_graph = self.synthesizer.synthesize([screen1, screen2])
        
        # Should normalize duplicate "search::products" actions
        self.assertEqual(task_graph.meta['total_actions'], 3)
        # Unique actions should be less (just 1 unique "search products")
        self.assertLessEqual(task_graph.meta['unique_actions'], 2)
    
    def test_task_grouping(self):
        """Test that related actions are grouped into tasks"""
        screen = Screen(
            screen_id="s1",
            url="https://example.com",
            dom_snapshot="",
            visible_text="",
            semantic_summary="",
            screen_type=ScreenType.SEARCH,
            timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="search", object="products", confidence=0.9, action_id="a1"),
            ActionSemantic(intent="filter", object="results", confidence=0.8, action_id="a2"),
        ]
        
        task_graph = self.synthesizer.synthesize([screen])
        
        # Should create "search products" task grouping search and filter
        search_tasks = [t for t in task_graph.tasks if "search" in t.name.lower()]
        self.assertGreater(len(search_tasks), 0)
        
        # The search task should contain both actions
        search_task = search_tasks[0]
        self.assertEqual(len(search_task.related_actions), 2)
    
    def test_priority_classification(self):
        """Test that tasks are classified correctly by priority"""
        screens = []
        
        # Initial task (search)
        s1 = Screen(
            screen_id="s1", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.HOMEPAGE, timestamp="2026-02-24"
        )
        s1.actions = [ActionSemantic(intent="search", object="items", confidence=0.9, action_id="a1")]
        screens.append(s1)
        
        # Intermediate task (view)
        s2 = Screen(
            screen_id="s2", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.PRODUCT_DETAIL, timestamp="2026-02-24"
        )
        s2.actions = [ActionSemantic(intent="view", object="details", confidence=0.9, action_id="a2")]
        screens.append(s2)
        
        # Terminal task (checkout)
        s3 = Screen(
            screen_id="s3", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.CHECKOUT, timestamp="2026-02-24"
        )
        s3.actions = [ActionSemantic(intent="checkout", object="order", confidence=0.9, action_id="a3")]
        screens.append(s3)
        
        task_graph = self.synthesizer.synthesize(screens)
        
        # Check priorities
        initial_tasks = task_graph.get_tasks_by_priority(TaskPriority.INITIAL)
        terminal_tasks = task_graph.get_tasks_by_priority(TaskPriority.TERMINAL)
        
        self.assertGreater(len(initial_tasks), 0, "Should have initial tasks")
        self.assertGreater(len(terminal_tasks), 0, "Should have terminal tasks")
    
    def test_confidence_computation(self):
        """Test that task confidence is computed correctly"""
        # Action appearing on multiple screens should boost confidence
        screens = []
        for i in range(3):
            screen = Screen(
                screen_id=f"s{i}",
                url=f"https://example.com/page{i}",
                dom_snapshot="",
                visible_text="",
                semantic_summary="",
                screen_type=ScreenType.SEARCH,
                timestamp="2026-02-24"
            )
            screen.actions = [
                ActionSemantic(
                    intent="search",
                    object="products",
                    confidence=0.7,  # Lower base confidence
                    action_id=f"a{i}"
                )
            ]
            screens.append(screen)
        
        task_graph = self.synthesizer.synthesize(screens)
        
        # Find search task
        search_tasks = [t for t in task_graph.tasks if "search" in t.name.lower()]
        self.assertGreater(len(search_tasks), 0)
        
        search_task = search_tasks[0]
        # Confidence should be boosted by appearing on multiple screens
        self.assertGreater(search_task.confidence, 0.7, "Confidence should be boosted")
    
    def test_task_sorting(self):
        """Test that tasks are sorted by priority then confidence"""
        screens = []
        
        # Terminal task with high confidence
        s1 = Screen(
            screen_id="s1", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.CART, timestamp="2026-02-24"
        )
        s1.actions = [ActionSemantic(intent="checkout", object="order", confidence=0.95, action_id="a1")]
        screens.append(s1)
        
        # Initial task with low confidence
        s2 = Screen(
            screen_id="s2", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.HOMEPAGE, timestamp="2026-02-24"
        )
        s2.actions = [ActionSemantic(intent="search", object="items", confidence=0.6, action_id="a2")]
        screens.append(s2)
        
        task_graph = self.synthesizer.synthesize(screens)
        
        # Initial tasks should come before terminal tasks regardless of confidence
        if len(task_graph.tasks) >= 2:
            first_task = task_graph.tasks[0]
            last_task = task_graph.tasks[-1]
            
            # Check priority ordering
            priority_order = {
                TaskPriority.INITIAL: 0,
                TaskPriority.INTERMEDIATE: 1,
                TaskPriority.TERMINAL: 2
            }
            self.assertLessEqual(
                priority_order[first_task.priority],
                priority_order[last_task.priority],
                "Tasks should be sorted by priority"
            )
    
    def test_task_serialization(self):
        """Test that tasks can be serialized to dict and back"""
        screen = Screen(
            screen_id="s1", url="https://example.com", dom_snapshot="",
            visible_text="", semantic_summary="", screen_type=ScreenType.HOMEPAGE,
            timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="search", object="products", confidence=0.9, action_id="a1")
        ]
        
        task_graph = self.synthesizer.synthesize([screen])
        
        # Serialize to dict
        task_dict = task_graph.to_dict()
        self.assertIsInstance(task_dict, dict)
        self.assertIn('tasks', task_dict)
        self.assertIn('meta', task_dict)
        
        # Deserialize back
        restored_graph = TaskGraph.from_dict(task_dict)
        self.assertEqual(len(restored_graph.tasks), len(task_graph.tasks))
        
        if len(task_graph.tasks) > 0:
            original_task = task_graph.tasks[0]
            restored_task = restored_graph.tasks[0]
            self.assertEqual(original_task.task_id, restored_task.task_id)
            self.assertEqual(original_task.name, restored_task.name)
            self.assertEqual(original_task.priority, restored_task.priority)
    
    def test_entry_screens_tracking(self):
        """Test that entry screens are tracked correctly"""
        screens = []
        
        # Same action on multiple screens
        for i in range(3):
            screen = Screen(
                screen_id=f"screen_{i}",
                url=f"https://example.com/page{i}",
                dom_snapshot="", visible_text="",
                semantic_summary="", screen_type=ScreenType.SEARCH,
                timestamp="2026-02-24"
            )
            screen.actions = [
                ActionSemantic(intent="search", object="products", confidence=0.9, action_id=f"a{i}")
            ]
            screens.append(screen)
        
        task_graph = self.synthesizer.synthesize(screens)
        
        # Find search task
        search_tasks = [t for t in task_graph.tasks if "search" in t.name.lower()]
        self.assertGreater(len(search_tasks), 0)
        
        search_task = search_tasks[0]
        # Should track all 3 entry screens
        self.assertEqual(len(search_task.entry_screens), 3)
        self.assertIn("screen_0", search_task.entry_screens)
        self.assertIn("screen_1", search_task.entry_screens)
        self.assertIn("screen_2", search_task.entry_screens)


class TestDomainSpecificPatterns(unittest.TestCase):
    """Test domain-specific pattern matching"""
    
    def test_ecommerce_patterns(self):
        """Test e-commerce domain patterns"""
        synthesizer = TaskSynthesizer(domain="ecommerce")
        
        screen = Screen(
            screen_id="s1", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.PRODUCT_DETAIL, timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="add", object="cart", confidence=0.9, action_id="a1")
        ]
        
        task_graph = synthesizer.synthesize([screen])
        
        # Should create "add to cart" task (e-commerce specific)
        cart_tasks = [t for t in task_graph.tasks if "cart" in t.name.lower()]
        self.assertGreater(len(cart_tasks), 0)
    
    def test_generic_patterns(self):
        """Test generic domain patterns"""
        synthesizer = TaskSynthesizer(domain="generic")
        
        screen = Screen(
            screen_id="s1", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.OTHER, timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="view", object="details", confidence=0.9, action_id="a1")
        ]
        
        task_graph = synthesizer.synthesize([screen])
        
        # Should create generic "view details" task
        view_tasks = [t for t in task_graph.tasks if "view" in t.name.lower()]
        self.assertGreater(len(view_tasks), 0)
    
    def test_custom_patterns(self):
        """Test custom pattern matching"""
        custom_patterns = [
            (['book', 'reserve'], "book service", "Book a service"),
            (['cancel'], "cancel booking", "Cancel reservation"),
        ]
        synthesizer = TaskSynthesizer(custom_patterns=custom_patterns)
        
        screen = Screen(
            screen_id="s1", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.FORM, timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="book", object="appointment", confidence=0.9, action_id="a1")
        ]
        
        task_graph = synthesizer.synthesize([screen])
        
        # Should match custom pattern
        book_tasks = [t for t in task_graph.tasks if "book" in t.name.lower()]
        self.assertGreater(len(book_tasks), 0)
    
    def test_auto_detection_ecommerce(self):
        """Test auto-detection for e-commerce sites"""
        synthesizer = TaskSynthesizer()  # No domain specified
        
        # Create screen with e-commerce indicators
        screen = Screen(
            screen_id="s1",
            url="https://shop.example.com/products",
            dom_snapshot="",
            visible_text="Buy products, add to cart, checkout",
            semantic_summary="Product listing page with shopping cart",
            screen_type=ScreenType.LISTING,
            timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="add", object="cart", confidence=0.9, action_id="a1")
        ]
        
        # Should auto-detect e-commerce
        detected_domain = synthesizer.auto_detect_domain([screen])
        self.assertEqual(detected_domain, "ecommerce")
    
    def test_auto_detection_news(self):
        """Test auto-detection for news sites"""
        synthesizer = TaskSynthesizer()
        
        screen = Screen(
            screen_id="s1",
            url="https://news.example.com/articles",
            dom_snapshot="",
            visible_text="Read latest news articles and blog posts",
            semantic_summary="News article listing with read more links",
            screen_type=ScreenType.ARTICLE,
            timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="read", object="article", confidence=0.9, action_id="a1")
        ]
        
        detected_domain = synthesizer.auto_detect_domain([screen])
        self.assertEqual(detected_domain, "news")
    
    def test_auth_patterns_included(self):
        """Test that authentication patterns are always included"""
        synthesizer = TaskSynthesizer(domain="ecommerce")
        
        screen = Screen(
            screen_id="s1", url="", dom_snapshot="", visible_text="",
            semantic_summary="", screen_type=ScreenType.LOGIN, timestamp="2026-02-24"
        )
        screen.actions = [
            ActionSemantic(intent="sign_in", object="account", confidence=0.9, action_id="a1")
        ]
        
        task_graph = synthesizer.synthesize([screen])
        
        # Should have sign in task (from AUTH_PATTERNS)
        signin_tasks = [t for t in task_graph.tasks if "sign" in t.name.lower()]
        self.assertGreater(len(signin_tasks), 0)


class TestTaskDataModels(unittest.TestCase):
    """Test Task and TaskGraph data models"""
    
    def test_task_creation(self):
        """Test creating a Task object"""
        task = Task(
            task_id="task_001",
            name="test task",
            description="Test description",
            related_actions=["a1", "a2"],
            confidence=0.85,
            entry_screens=["s1", "s2"],
            priority=TaskPriority.INTERMEDIATE
        )
        
        self.assertEqual(task.task_id, "task_001")
        self.assertEqual(task.name, "test task")
        self.assertEqual(task.priority, TaskPriority.INTERMEDIATE)
        self.assertEqual(len(task.related_actions), 2)
    
    def test_task_graph_creation(self):
        """Test creating a TaskGraph"""
        task1 = Task(
            task_id="t1", name="Task 1", description="", related_actions=[],
            confidence=0.9, entry_screens=[], priority=TaskPriority.INITIAL
        )
        task2 = Task(
            task_id="t2", name="Task 2", description="", related_actions=[],
            confidence=0.8, entry_screens=[], priority=TaskPriority.TERMINAL
        )
        
        task_graph = TaskGraph(tasks=[task1, task2])
        
        self.assertEqual(len(task_graph.tasks), 2)
        self.assertEqual(task_graph.get_task_by_id("t1"), task1)
        self.assertEqual(task_graph.get_task_by_id("t2"), task2)
    
    def test_get_tasks_by_priority(self):
        """Test filtering tasks by priority"""
        tasks = [
            Task(
                task_id=f"t{i}", name=f"Task {i}", description="",
                related_actions=[], confidence=0.8, entry_screens=[],
                priority=priority
            )
            for i, priority in enumerate([
                TaskPriority.INITIAL,
                TaskPriority.INTERMEDIATE,
                TaskPriority.TERMINAL,
                TaskPriority.INITIAL
            ])
        ]
        
        task_graph = TaskGraph(tasks=tasks)
        
        initial_tasks = task_graph.get_tasks_by_priority(TaskPriority.INITIAL)
        intermediate_tasks = task_graph.get_tasks_by_priority(TaskPriority.INTERMEDIATE)
        terminal_tasks = task_graph.get_tasks_by_priority(TaskPriority.TERMINAL)
        
        self.assertEqual(len(initial_tasks), 2)
        self.assertEqual(len(intermediate_tasks), 1)
        self.assertEqual(len(terminal_tasks), 1)


if __name__ == '__main__':
    unittest.main()
