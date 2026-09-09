from surv4impact.knowledge import load_catalog, load_pilot_rules, p0_catalog


def test_matrix_inventory_matches_pilot_scope():
    assert len(load_catalog()) == 29
    assert len(p0_catalog()) == 15
    assert len(load_pilot_rules()) == 20
    assert {rule["rule_id"] for rule in load_pilot_rules()} >= {
        "D2.1.03-META-01",
        "D2.1.03-COMP-01",
        "D2.1.03-GLOBAL-01",
    }

