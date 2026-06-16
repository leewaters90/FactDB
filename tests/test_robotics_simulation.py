from factdb.models import Fact
from factdb.robotics_simulation import RoboticsSimulationWorkflow


class TestRoboticsSimulationWorkflow:
    def test_iteration_recovers_after_injected_loss(self, db_session):
        workflow = RoboticsSimulationWorkflow(db_session, scenario_name="arena-alpha")
        report = workflow.run_iteration(max_steps=80, inject_loss=True)

        assert report["episode"]["success"] is True
        assert report["replay"]["success"] is True
        assert report["refill"]["repaired_or_created"] >= 1
        assert report["refill"]["post_validation"]["invalid_count"] == 0
        assert report["success_criteria"]["stable_task_completion"] is True
        assert report["success_criteria"]["no_integrity_regressions"] is True

    def test_iterations_produce_verified_simulation_facts(self, db_session):
        workflow = RoboticsSimulationWorkflow(db_session, scenario_name="arena-alpha")
        report = workflow.run_iterations(iterations=2, max_steps=80, inject_loss=False)

        assert report["all_successful"] is True
        assert len(report["iterations"]) == 2

        sim_facts = [
            fact
            for fact in db_session.query(Fact).all()
            if fact.source_url and fact.source_url.startswith("sim://fps/")
        ]
        assert len(sim_facts) > 0
        assert all(fact.status == "verified" for fact in sim_facts)
