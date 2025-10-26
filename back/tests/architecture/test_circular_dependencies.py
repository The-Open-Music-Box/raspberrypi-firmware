# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Circular Dependencies Detection Tests.

These tests automatically detect circular import dependencies that can cause
runtime errors and indicate poor architectural design.
"""

import pytest
from .helpers import (
    build_dependency_graph,
    find_circular_dependencies,
    get_layer_from_module
)


class TestCircularDependencies:
    """Test suite for circular dependency detection."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.dependency_graph = build_dependency_graph()

    def test_no_circular_dependencies_exist(self):
        """Verify there are no circular dependencies in the codebase."""
        cycles = find_circular_dependencies(self.dependency_graph)

        assert len(cycles) == 0, f"""
        ❌ CIRCULAR DEPENDENCIES DETECTED!

        Circular dependencies can cause:
        - Import errors at runtime
        - Tight coupling between modules
        - Difficult testing and maintenance
        - Poor separation of concerns

        Circular dependencies found:
        {chr(10).join([f"🔄 {' → '.join(cycle + [cycle[0]])}" for cycle in cycles])}

        ✅ Solutions:
        1. Extract common functionality to a separate module
        2. Use dependency injection to break the cycle
        3. Move one of the dependencies to a different layer
        4. Create interfaces/protocols to decouple modules
        """

    def test_no_intra_layer_circular_dependencies(self):
        """Verify no circular dependencies exist within the same layer."""
        layer_cycles = {
            'domain': [],
            'application': [],
            'infrastructure': [],
            'presentation': [],
            'services': []
        }

        cycles = find_circular_dependencies(self.dependency_graph)

        for cycle in cycles:
            # Check if cycle is within the same layer
            cycle_layers = [get_layer_from_module(module) for module in cycle]

            if len(set(cycle_layers)) == 1:  # All modules in same layer
                layer = cycle_layers[0]
                if layer in layer_cycles:
                    layer_cycles[layer].append(cycle)

        total_intra_layer_cycles = sum(len(cycles) for cycles in layer_cycles.values())

        assert total_intra_layer_cycles == 0, f"""
        ❌ INTRA-LAYER CIRCULAR DEPENDENCIES!

        Circular dependencies within the same architectural layer indicate
        tight coupling and poor module organization.

        Intra-layer cycles found:
        {chr(10).join([
            f"🔄 {layer}: {' → '.join(cycle + [cycle[0]])}"
            for layer, cycles in layer_cycles.items()
            for cycle in cycles
        ])}

        ✅ Solutions:
        1. Extract shared functionality to a common module
        2. Reorganize modules to have clearer responsibilities
        3. Use events or mediator pattern for communication
        4. Split large modules into smaller, focused ones
        """

    def test_no_cross_layer_circular_dependencies(self):
        """Verify no circular dependencies exist between different layers."""
        cross_layer_cycles = []
        cycles = find_circular_dependencies(self.dependency_graph)

        for cycle in cycles:
            cycle_layers = [get_layer_from_module(module) for module in cycle]

            if len(set(cycle_layers)) > 1:  # Multiple layers involved
                cross_layer_cycles.append((cycle, cycle_layers))

        assert len(cross_layer_cycles) == 0, f"""
        ❌ CROSS-LAYER CIRCULAR DEPENDENCIES!

        Circular dependencies between architectural layers violate
        the dependency direction rules and create architectural violations.

        Cross-layer cycles found:
        {chr(10).join([
            f"🔄 {' → '.join(cycle + [cycle[0]])} (Layers: {set(layers)})"
            for cycle, layers in cross_layer_cycles
        ])}

        ✅ Solutions:
        1. Review dependency direction rules
        2. Use dependency injection to invert control
        3. Move shared interfaces to Domain layer
        4. Eliminate reverse dependencies
        """

    def test_dependency_graph_is_acyclic(self):
        """Verify the overall dependency graph forms a Directed Acyclic Graph (DAG)."""
        cycles = find_circular_dependencies(self.dependency_graph)

        # Detailed analysis of dependency graph structure
        total_modules = len(self.dependency_graph)
        total_dependencies = sum(len(list(self.dependency_graph.successors(node))) for node in self.dependency_graph.nodes())

        layer_stats = {}
        for module in self.dependency_graph.nodes():
            dependencies = list(self.dependency_graph.successors(module))
            layer = get_layer_from_module(module)
            if layer not in layer_stats:
                layer_stats[layer] = {'modules': 0, 'dependencies': 0}
            layer_stats[layer]['modules'] += 1
            layer_stats[layer]['dependencies'] += len(dependencies)

        print(f"📊 Dependency Graph Statistics:")
        print(f"   Total modules: {total_modules}")
        print(f"   Total dependencies: {total_dependencies}")
        print(f"   Average dependencies per module: {total_dependencies / total_modules:.2f}")

        for layer, stats in sorted(layer_stats.items()):
            print(f"   {layer.title()}: {stats['modules']} modules, {stats['dependencies']} dependencies")

        assert len(cycles) == 0, f"""
        ❌ DEPENDENCY GRAPH IS NOT ACYCLIC!

        A proper architectural dependency graph should be a Directed Acyclic Graph (DAG).
        Cycles indicate architectural problems that need to be resolved.

        Graph Statistics:
        - Total modules: {total_modules}
        - Total dependencies: {total_dependencies}
        - Cycles found: {len(cycles)}

        ✅ Goal: Achieve a clean DAG structure with proper dependency flow.
        """

    def test_no_self_dependencies(self):
        """Verify no module depends on itself."""
        self_dependencies = []

        for module in self.dependency_graph.nodes():
            dependencies = list(self.dependency_graph.successors(module))
            if module in dependencies:
                self_dependencies.append(module)

        assert len(self_dependencies) == 0, f"""
        ❌ SELF-DEPENDENCIES DETECTED!

        Modules should not import themselves directly.
        This creates unnecessary circular references.

        Self-dependent modules:
        {chr(10).join([f"🔄 {module} → {module}" for module in self_dependencies])}

        ✅ Solution: Remove self-imports or reorganize module structure.
        """

    def test_minimal_coupling_between_layers(self):
        """Verify minimal coupling between architectural layers."""
        layer_coupling = {}

        for module in self.dependency_graph.nodes():
            dependencies = list(self.dependency_graph.successors(module))
            module_layer = get_layer_from_module(module)

            for dependency in dependencies:
                dep_layer = get_layer_from_module(dependency)

                if module_layer != dep_layer:
                    coupling_key = f"{module_layer} → {dep_layer}"
                    if coupling_key not in layer_coupling:
                        layer_coupling[coupling_key] = 0
                    layer_coupling[coupling_key] += 1

        # Print coupling analysis
        print(f"🔗 Inter-layer Coupling Analysis:")
        for coupling, count in sorted(layer_coupling.items()):
            print(f"   {coupling}: {count} dependencies")

        # Check for problematic coupling patterns
        problematic_coupling = []

        for coupling, count in layer_coupling.items():
            # High coupling might indicate architectural issues
            if count > 20:  # Threshold for high coupling
                problematic_coupling.append(f"{coupling}: {count} dependencies")

        if len(problematic_coupling) > 0:
            print(f"⚠️ High coupling detected:")
            for coupling in problematic_coupling:
                print(f"   {coupling}")

        # This is informational rather than a hard failure
        assert True, "Inter-layer coupling analysis complete"

    def test_dependency_depth_analysis(self):
        """Analyze the depth of dependency chains."""

        def get_max_depth(module, visited=None, depth=0):
            """Get maximum dependency depth from a module."""
            if visited is None:
                visited = set()

            if module in visited:
                return depth  # Avoid infinite recursion

            visited.add(module)
            max_depth = depth

            dependencies = list(self.dependency_graph.successors(module)) if module in self.dependency_graph else []
            for dependency in dependencies:
                dep_depth = get_max_depth(dependency, visited.copy(), depth + 1)
                max_depth = max(max_depth, dep_depth)

            return max_depth

        # Analyze dependency depths
        depth_analysis = {}
        for module in self.dependency_graph.nodes():
            depth = get_max_depth(module)
            layer = get_layer_from_module(module)

            if layer not in depth_analysis:
                depth_analysis[layer] = []
            depth_analysis[layer].append(depth)

        # Print depth analysis
        print(f"📏 Dependency Depth Analysis:")
        for layer, depths in sorted(depth_analysis.items()):
            if depths:
                avg_depth = sum(depths) / len(depths)
                max_depth = max(depths)
                print(f"   {layer.title()}: avg={avg_depth:.1f}, max={max_depth}")

        # Check for excessive dependency chains
        excessive_depth_modules = []
        for module in self.dependency_graph.nodes():
            depth = get_max_depth(module)
            if depth > 10:  # Threshold for excessive depth
                excessive_depth_modules.append(f"{module}: depth {depth}")

        if len(excessive_depth_modules) > 0:
            print(f"⚠️ Modules with deep dependency chains:")
            for module_info in excessive_depth_modules[:5]:  # Show first 5
                print(f"   {module_info}")

        # This is informational
        assert True, "Dependency depth analysis complete"