"""The run receipt is the only thing standing between an aggregate number and
'trust me'.  Its hash must be reproducible by anyone, from the documented
serialization alone."""

import hashlib
import json

import pytest

from skillshift.errors import ReceiptError
from skillshift.eval import metrics, receipt, schema
from skillshift.eval.records import TaskRecord


def make_records(n=4, *, failures=0):
    return tuple(
        TaskRecord(
            uid=f"skillshift.gitlab.v1.{i}",
            site="gitlab",
            condition="src",
            success=i % 2 == 0,
            steps=3 + i,
            skill_calls=2,
            skill_failures=failures,
        )
        for i in range(n)
    )


class TestCommitment:
    def test_canonical_form_matches_the_documented_serialization(self):
        # Recomputed here by hand, independently of the implementation, because
        # a third party has to be able to do exactly this.
        records = make_records(2)
        expected = (
            "skillshift/per-task-v1\n"
            "skillshift.gitlab.v1.0\tsrc\t1\t3\t2\t0\n"
            "skillshift.gitlab.v1.1\tsrc\t0\t4\t2\t0\n"
        )
        assert receipt.canonical_per_task_form(records) == expected

    def test_digest_matches_sha256_of_the_canonical_form(self):
        records = make_records(3)
        body = receipt.canonical_per_task_form(records)
        assert (
            receipt.per_task_commitment(records)["value"]
            == hashlib.sha256(body.encode("utf-8")).hexdigest()
        )

    def test_digest_is_independent_of_record_order(self):
        records = make_records(5)
        assert (
            receipt.per_task_commitment(records)["value"]
            == receipt.per_task_commitment(tuple(reversed(records)))["value"]
        )

    @pytest.mark.parametrize(
        "field,value",
        [("success", True), ("steps", 99), ("skill_calls", 7), ("skill_failures", 1)],
    )
    def test_changing_any_field_changes_the_digest(self, field, value):
        # records[1] has success=False, steps=4, skill_calls=2, skill_failures=0,
        # so each parametrized value is a real change.
        records = make_records(3)
        before = receipt.per_task_commitment(records)["value"]

        tampered = (
            *records[:1],
            type(records[1])(**{**records[1].to_dict(), field: value}),
            *records[2:],
        )

        assert receipt.per_task_commitment(tampered)["value"] != before

    def test_commitment_records_the_count_and_the_format_version(self):
        commitment = receipt.per_task_commitment(make_records(6))
        assert commitment["n_records"] == 6
        assert commitment["algorithm"] == "sha256"
        assert commitment["canonical_form"] == "skillshift/per-task-v1"

    def test_empty_records_are_rejected(self):
        with pytest.raises(ReceiptError):
            receipt.per_task_commitment(())

    def test_duplicate_uids_in_the_same_condition_are_rejected(self):
        records = make_records(2)
        with pytest.raises(ReceiptError):
            receipt.per_task_commitment(records + records[:1])


class TestBuildReceipt:
    def build(self, **overrides):
        records = make_records(4)
        cells = tuple(
            metrics.CellStats(
                site=site,
                condition=condition,
                n={"gitlab": 162, "magento": 114, "wordpress": 79}[site],
                sr=40.0,
                avg_steps=6.0,
                asc=0.1,
                sfr=20.0,
                n_skill_calls=50,
                sfr_low_confidence=False,
            )
            for site in ("gitlab", "magento", "wordpress")
            for condition in metrics.CONDITIONS
        )
        kwargs = dict(
            records=records,
            aggregate=metrics.aggregate(cells),
            model={"id": "gpt-5-mini-2025-08-07", "temperature": 0.0, "vision": True},
            env_digests={"gitlab-v12": "sha256:" + "ab" * 32},
            harness_commit="a1b2c3d",
            timestamp="2026-09-01T00:00:00Z",
        )
        kwargs.update(overrides)
        return receipt.build_receipt(**kwargs)

    def test_receipt_validates_against_its_schema(self):
        assert schema.validate(self.build(), "receipt") == ()

    def test_receipt_carries_every_required_provenance_field(self):
        built = self.build()
        for field in (
            "harness_version",
            "env_digests",
            "model",
            "n_per_cell",
            "aggregate",
            "per_task_commitment",
            "timestamp",
        ):
            assert field in built

    def test_n_per_cell_uses_the_official_task_counts(self):
        built = self.build()
        assert built["n_per_cell"]["gitlab"]["src"] == 162
        assert built["n_per_cell"]["magento"]["tgt-exec"] == 114
        assert built["n_per_cell"]["wordpress"]["src-perc"] == 79

    def test_aggregate_is_embedded_verbatim(self):
        built = self.build()
        assert set(built["aggregate"]) == {"metrics", "n"}
        assert built["aggregate"]["metrics"]["SR"]["overall"] == pytest.approx(40.0)

    def test_receipt_is_json_serializable(self):
        json.dumps(self.build())

    def test_rejects_a_malformed_env_digest(self):
        with pytest.raises(ReceiptError):
            self.build(env_digests={"gitlab-v12": "not-a-digest"})

    def test_rejects_an_empty_model_id(self):
        with pytest.raises(ReceiptError):
            self.build(model={"id": ""})


class TestVerify:
    def test_matching_records_verify(self):
        records = make_records(4)
        commitment = receipt.per_task_commitment(records)
        receipt.verify_commitment(records, commitment)

    def test_tampered_records_are_rejected_with_both_digests_shown(self):
        commitment = receipt.per_task_commitment(make_records(4))
        with pytest.raises(ReceiptError) as excinfo:
            receipt.verify_commitment(make_records(4, failures=1), commitment)
        assert commitment["value"][:12] in str(excinfo.value)

    def test_a_different_canonical_form_version_is_rejected(self):
        commitment = dict(receipt.per_task_commitment(make_records(2)))
        commitment["canonical_form"] = "skillshift/per-task-v2"
        with pytest.raises(ReceiptError):
            receipt.verify_commitment(make_records(2), commitment)
