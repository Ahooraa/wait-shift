"""Guard: every constant stated in the paper must equal the value in config/paper_constants.yaml.
The expected values below are an INDEPENDENT copy typed from the paper (p.9-p.10 Tab.2, Sec.4.4, 5.1, 5.2)."""
from dfps.constants import PAPER as P


def test_table2_values():
    assert (P["function_runtime_s"]["min"], P["function_runtime_s"]["max"]) == (2, 10)
    assert (P["cold_start_delay_s"]["min"], P["cold_start_delay_s"]["max"]) == (2, 10)
    assert (P["intermediate_state_mb"]["min"], P["intermediate_state_mb"]["max"]) == (10, 50)
    assert P["number_of_workflows"]["default"] == 15
    assert P["number_of_edge_nodes"]["default"] == 80
    assert P["average_bandwidth_mb_s"]["value"] == 50
    assert (P["edge_node_function_capacity"]["min"], P["edge_node_function_capacity"]["max"]) == (5, 25)
    assert (P["edge_node_storage_capacity_gb"]["min"], P["edge_node_storage_capacity_gb"]["max"]) == (10, 30)
    assert (P["incoming_request_rate_per_s"]["min"], P["incoming_request_rate_per_s"]["max"]) == (0.5, 100)
    assert P["replacement_interval_s"]["value"] == 4


def test_text_values():
    assert P["propagation_delay_s"]["value"] == 0
    assert (P["uniform_workload_mean_ms"]["min"], P["uniform_workload_mean_ms"]["max"]) == (200, 700)
    pw = P["pareto_workload"]
    assert (pw["high_rate_fraction"], pw["high_mean_ms_min"], pw["high_mean_ms_max"]) == (0.2, 50, 100)
    assert (pw["low_mean_s_min"], pw["low_mean_s_max"]) == (2, 4)
    assert tuple(P["arrival_scaling_factors"]["values"]) == (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)
    assert P["workloads_per_experiment"]["value"] == 10
    assert P["significance_level"]["value"] == 0.05
    assert P["nsga2_population_size"]["value"] == 100
    assert P["nsga2_objectives"]["value"] == 2
    assert P["alibaba_job_max_execution_s"]["value"] == 60
    assert (P["number_of_workflows"]["scenario3_min"], P["number_of_workflows"]["scenario3_max"]) == (5, 40)
    assert (P["number_of_edge_nodes"]["scenario2_min"], P["number_of_edge_nodes"]["scenario2_max"]) == (20, 160)
    assert (P["replacement_interval_s"]["sweep_min"], P["replacement_interval_s"]["sweep_max"]) == (1, 9)
