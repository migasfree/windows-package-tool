import pytest

from wpt.package_manager import PackageManager


@pytest.fixture
def pms():
    return PackageManager()


def test_no_dependencies(pms):
    pms._repository_info = {'package-a': {'1.0.0': {'metadata': {}}}}
    result = pms.resolve_dependencies('package-a', '1.0.0')
    assert result == {'package-a': '1.0.0'}


def test_single_dependency_installed(pms):
    pms._repository_info = {'package-b': {'2.0.0': {'metadata': {}}}, 'dependency-a': {'3.0.0': {'metadata': {}}}}
    result = pms.resolve_dependencies('package-b', '2.0.0', {'dependency-a': '3.0.0'})
    assert result == {'package-b': '2.0.0', 'dependency-a': '3.0.0'}


def test_single_dependency_not_installed(pms):
    pms._repository_info = {
        'package-b': {'2.0.0': {'metadata': {'dependencies': ['dependency-a (>= 4.0.0)']}}},
        'dependency-a': {'3.0.0': {'metadata': {}}, '4.0.0': {'metadata': {}}},
    }
    result = pms.resolve_dependencies('package-b', '2.0.0')
    assert result == {'package-b': '2.0.0', 'dependency-a': '4.0.0'}


def test_single_dependency_not_available(pms):
    pms._repository_info = {
        'package-b': {'2.0.0': {'metadata': {'dependencies': ['dependency-b (> 1.0.0)']}}},
        'dependency-b': {'1.0.0': {'metadata': {}}},
    }
    with pytest.raises(ValueError):
        pms.resolve_dependencies('package-b', '2.0.0')


"""
def test_single_dependency_invalid_version_condition(pms):
    with pytest.raises(ValueError):
        pms.resolve_dependencies('package-b', '2.0.0', {'dependency-a': '2.0.0'})
"""


def test_resolve_dependencies_simple(pms):
    package_name = 'package1'
    package_version = '1.0.0'
    installed_packages = {'package1': '1.0.0'}
    pms._repository_info = {'package1': {'1.0.0': {'metadata': {'dependencies': []}}}}

    result = pms.resolve_dependencies(package_name, package_version, installed_packages)
    assert result == {package_name: package_version}


def test_resolve_dependencies_with_dependencies(pms):
    package_name = 'package1'
    package_version = '1.0.0'
    installed_packages = {'package1': '1.0.0', 'package2': '2.0.0'}
    pms._repository_info = {
        'package1': {'1.0.0': {'metadata': {'dependencies': ['package2']}}},
        'package2': {'2.0.0': {'metadata': {'dependencies': []}}},
    }

    result = pms.resolve_dependencies(package_name, package_version, installed_packages)
    assert result == installed_packages


def test_resolve_dependencies_with_circular_dependencies(pms):
    package_name = 'package1'
    package_version = '1.0.0'
    pms._repository_info = {
        'package1': {'1.0.0': {'metadata': {'dependencies': ['package2']}}},
        'package2': {'2.0.0': {'metadata': {'dependencies': ['package1']}}},
    }

    with pytest.raises(ValueError):
        pms.resolve_dependencies(package_name, package_version)


def test_self_circular_dependencies(pms):
    package_name = 'package1'
    package_version = '1.0.0'
    pms._repository_info = {'package1': {'1.0.0': {'metadata': {'dependencies': ['package1']}}}}

    with pytest.raises(ValueError):
        pms.resolve_dependencies(package_name, package_version)


def test_resolve_dependencies_with_unknown_package(pms):
    package_name = 'package3'
    package_version = '3.0.0'
    installed_packages = {'package1': '1.0.0', 'package2': '2.0.0'}
    pms._repository_info = {
        'package1': {'1.0.0': {'metadata': {'dependencies': []}}},
        'package2': {'2.0.0': {'metadata': {'dependencies': []}}},
    }

    with pytest.raises(KeyError):
        pms.resolve_dependencies(package_name, package_version, installed_packages)


def test_dag_dependency(pms):
    """Test that a package can have dependencies that share a common dependency without raising circular dependency."""
    pms._repository_info = {
        'package-a': {'1.0.0': {'metadata': {'dependencies': ['package-b', 'package-c']}}},
        'package-b': {'1.0.0': {'metadata': {'dependencies': ['package-c']}}},
        'package-c': {'1.0.0': {'metadata': {}}},
    }
    result = pms.resolve_dependencies('package-a', '1.0.0')
    assert result == {'package-a': '1.0.0', 'package-b': '1.0.0', 'package-c': '1.0.0'}
