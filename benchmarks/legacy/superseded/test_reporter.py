from repair_runner_v2 import check_contamination, dump_manifest

# Contamination tests
def test_contamination():
    # Baseline
    m_baseline = {"mode": "BASELINE", "skills": {}, "config_plugins": {"gravitas": {"enabled": False}}}
    check_contamination(m_baseline, "BASELINE") # should pass
    try:
        check_contamination({"mode": "BASELINE", "skills": {"gravitas": "exists"}, "config_plugins": {}}, "BASELINE")
        assert False, "Should have failed"
    except AssertionError:
        pass

    # Core
    m_core = {"mode": "GRAVITAS_CORE", "skills": {"gravitas": "exists"}, "config_plugins": {"gravitas": {"enabled": False}}}
    check_contamination(m_core, "GRAVITAS_CORE") # should pass
    
    # Native
    m_native = {"mode": "GRAVITAS_NATIVE", "skills": {"gravitas": "exists"}, "config_plugins": {"gravitas": {"enabled": True}}}
    check_contamination(m_native, "GRAVITAS_NATIVE") # should pass

test_contamination()
print("REPORTER TESTS PASSED")
