from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from procedure_ci.cli import main
from procedure_ci.engine import analyze
from procedure_ci.errors import InputError
from procedure_ci.loader import MAX_REF_DEPTH, load_document
from procedure_ci.oas_index import build_oas_index

FIXTURES = Path(__file__).parent / "fixtures" / "webhook_onboarding"
BASE_OPENAPI = FIXTURES / "base" / "openapi.yaml"
HEAD_OPENAPI = FIXTURES / "head" / "openapi.yaml"
WORKFLOW = FIXTURES / "workflow.yaml"


@pytest.fixture()
def source_documents() -> tuple[dict, dict, dict]:
    yaml = YAML(typ="safe")
    return (
        yaml.load(BASE_OPENAPI.read_text(encoding="utf-8")),
        yaml.load(HEAD_OPENAPI.read_text(encoding="utf-8")),
        yaml.load(WORKFLOW.read_text(encoding="utf-8")),
    )


def write_documents(
    tmp_path: Path, base: dict, head: dict, workflow: dict | None = None
) -> tuple[Path, Path, Path]:
    yaml = YAML()
    base_path = tmp_path / "base.yaml"
    head_path = tmp_path / "head.yaml"
    workflow_path = tmp_path / "workflow.yaml"
    yaml.dump(base, base_path)
    yaml.dump(head, head_path)
    yaml.dump(
        workflow
        if workflow is not None
        else YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8")),
        workflow_path,
    )
    return base_path, head_path, workflow_path


def write_case(tmp_path: Path, head: dict, workflow: dict | None = None) -> tuple[Path, Path, Path]:
    yaml = YAML(typ="safe")
    base = yaml.load(BASE_OPENAPI.read_text(encoding="utf-8"))
    return write_documents(tmp_path, base, head, workflow)


def run_case(tmp_path: Path, head: dict, workflow: dict | None = None):
    paths = write_case(tmp_path, head, workflow)
    return analyze(*paths)


def test_clean_head_change_in_unrelated_operation_has_no_impact(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["paths"]["/health"]["get"]["summary"] = "Health endpoint"
    report = run_case(tmp_path, head)
    assert report.to_dict()["summary"] == {
        "workflows": 0,
        "affectedSteps": 0,
        "errors": 0,
        "reviews": 0,
        "unknowns": 0,
    }


def test_required_field_change_invalidates_literal_payload(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    schema = head["components"]["schemas"]["WebhookSubscription"]
    schema["required"].append("secret")
    schema["properties"]["secret"] = {"type": "string"}
    report = run_case(tmp_path, head)
    assert any(item.step.step_id == "createSubscription" for item in report.impacts)
    assert "EXAMPLE_SCHEMA_INVALID" in {item.code for item in report.diagnostics}
    assert report.summary()["errors"] == 1


def test_nested_ref_enum_change_maps_to_create_step_review(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["components"]["schemas"]["EventType"]["enum"] = ["push"]
    report = run_case(tmp_path, head)
    step_ids = {item.step.step_id for item in report.impacts}
    assert step_ids == {
        "createSubscription",
        "sendTest",
        "inspectDelivery",
        "deleteSubscription",
    }
    assert any(
        item.code == "DEPENDENCY_CHANGED"
        and item.affected_steps[0].step_id == "createSubscription"
        and item.details["change"]["entity"]["canonicalId"] == "EventType"
        for item in report.diagnostics
    )
    assert report.summary()["errors"] == 0


def test_response_change_reaches_consumer_with_explainable_path(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    response_schema = head["components"]["schemas"]["Subscription"]
    response_schema["properties"]["createdAt"] = {"type": "string"}
    response_schema["required"].append("createdAt")
    report = run_case(tmp_path, head)
    inspect_impact = next(item for item in report.impacts if item.step.step_id == "sendTest")
    assert any(change.entity.canonical_id == "Subscription" for change in inspect_impact.changes)
    assert any(
        [entity.kind for entity in path] == ["workflow_step", "operation", "schema"]
        and [entity.canonical_id for entity in path]
        == ["webhookOnboarding:createSubscription", "createWebhookSubscription", "Subscription"]
        for path in inspect_impact.dependency_paths
    )


def test_output_change_reaches_two_hop_consumer_with_full_step_chain(source_documents, tmp_path):
    _, head, workflow = source_documents
    head = copy.deepcopy(head)
    workflow = copy.deepcopy(workflow)
    inspect = workflow["workflows"][0]["steps"][2]
    inspect["parameters"] = [
        parameter
        for parameter in inspect["parameters"]
        if "sendTest.outputs" in parameter.get("value", "")
    ]
    subscription = head["components"]["schemas"]["Subscription"]
    subscription["properties"]["createdAt"] = {"type": "string"}
    subscription["required"].append("createdAt")
    report = run_case(tmp_path, head, workflow)
    inspect_impact = next(item for item in report.impacts if item.step.step_id == "inspectDelivery")
    assert any(
        [entity.kind for entity in path]
        == ["workflow_step", "workflow_step", "operation", "schema"]
        and [entity.canonical_id for entity in path]
        == [
            "webhookOnboarding:sendTest",
            "webhookOnboarding:createSubscription",
            "createWebhookSubscription",
            "Subscription",
        ]
        for path in inspect_impact.dependency_paths
    )


def test_security_change_maps_to_send_step(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    send_test = head["paths"]["/webhooks/{webhookId}/test"]["post"]
    send_test["security"] = [{"bearerAuth": []}]
    head["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
    }
    report = run_case(tmp_path, head)
    assert {item.step.step_id for item in report.impacts} == {"sendTest", "inspectDelivery"}
    assert report.summary()["errors"] == 0


def test_root_security_is_inherited_but_explicit_empty_security_is_not(source_documents, tmp_path):
    base, head, workflow = source_documents
    base = copy.deepcopy(base)
    head = copy.deepcopy(head)
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"].append({"stepId": "health", "operationId": "healthCheck"})
    head["security"] = [{"apiKey": []}]
    report = run_case(tmp_path, head, workflow)
    assert {item.step.step_id for item in report.impacts} == {"health"}
    assert any(change.entity.kind == "security" for change in report.impacts[0].changes)

    base["paths"]["/health"]["get"]["security"] = []
    head["paths"]["/health"]["get"]["security"] = []
    base["paths"]["/health"]["get"]["summary"] = head["paths"]["/health"]["get"]["summary"]
    report = analyze(*write_documents(tmp_path, base, head, workflow))
    assert not any(item.step.step_id == "health" for item in report.impacts)


def test_security_set_reordering_is_not_a_change(source_documents, tmp_path):
    base, head, workflow = source_documents
    base = copy.deepcopy(base)
    head = copy.deepcopy(head)
    workflow = copy.deepcopy(workflow)
    base["security"] = [{"apiKey": []}, {"apiKey": [], "other": ["read"]}]
    head["security"] = [{"apiKey": [], "other": ["read"]}, {"apiKey": []}]
    head["components"]["securitySchemes"]["other"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-Other",
    }
    base["components"]["securitySchemes"]["other"] = copy.deepcopy(
        head["components"]["securitySchemes"]["other"]
    )
    workflow["workflows"][0]["steps"].append({"stepId": "health", "operationId": "healthCheck"})
    report = analyze(*write_documents(tmp_path, base, head, workflow))
    assert not any(
        change.entity.kind == "security" for item in report.impacts for change in item.changes
    )


def test_parameters_merge_by_location_and_header_name_case(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    path_item = head["paths"]["/webhooks/{webhookId}/test"]
    path_item["parameters"] = [
        {
            "name": "X-Trace",
            "in": "header",
            "required": False,
            "schema": {"type": "string"},
        }
    ]
    path_item["post"]["parameters"].append(
        {
            "name": "x-trace",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        }
    )
    _, head_path, _ = write_case(tmp_path, head)
    index = build_oas_index(load_document(head_path))
    operation = index.operation("sendTestEvent")
    assert operation is not None
    parameters = operation.value["parameters"]
    assert len(parameters) == 2  # webhookId plus one merged header parameter
    header = next(item for item in parameters if item.get("in") == "header")
    assert header["name"] == "x-trace"
    assert header["required"] is True


def test_response_header_case_change_is_not_reported(source_documents, tmp_path):
    base, head, workflow = source_documents
    base = copy.deepcopy(base)
    head = copy.deepcopy(head)
    workflow = copy.deepcopy(workflow)
    base["paths"]["/webhooks"]["post"]["responses"]["201"]["headers"] = {
        "X-Trace": {"schema": {"type": "string"}}
    }
    head["paths"]["/webhooks"]["post"]["responses"]["201"]["headers"] = {
        "x-trace": {"schema": {"type": "string"}}
    }
    report = analyze(*write_documents(tmp_path, base, head, workflow))
    assert not any(item.step.step_id == "createSubscription" for item in report.impacts)


def test_removed_referenced_operation_is_deterministic_error(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    del head["paths"]["/webhooks/{webhookId}/test"]
    report = run_case(tmp_path, head)
    missing = [item for item in report.diagnostics if item.code == "OAS_OPERATION_MISSING"]
    assert len(missing) == 1
    assert missing[0].affected_steps[0].step_id == "sendTest"
    inspect_impact = next(item for item in report.impacts if item.step.step_id == "inspectDelivery")
    assert any(change.entity.canonical_id == "sendTestEvent" for change in inspect_impact.changes)
    assert any(
        entity.source_pointer.endswith("/post") and entity.canonical_id == "sendTestEvent"
        for path in inspect_impact.dependency_paths
        for entity in path
    )
    assert report.summary()["errors"] == 1


def test_missing_producer_operation_propagates_through_depends_on(source_documents, tmp_path):
    base, head, workflow = source_documents
    base = copy.deepcopy(base)
    head = copy.deepcopy(head)
    workflow = copy.deepcopy(workflow)
    inspect = workflow["workflows"][0]["steps"][2]
    inspect["parameters"] = []
    inspect["dependsOn"] = ["sendTest"]
    del base["paths"]["/webhooks"]
    del head["paths"]["/webhooks"]
    report = analyze(*write_documents(tmp_path, base, head, workflow))
    inspect_impact = next(item for item in report.impacts if item.step.step_id == "inspectDelivery")
    assert inspect_impact.severity == "review"
    assert any(
        [entity.canonical_id for entity in path]
        == ["webhookOnboarding:sendTest", "webhookOnboarding:createSubscription"]
        for path in inspect_impact.dependency_paths
    )


def test_same_operation_id_moved_path_is_review(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    operation = head["paths"].pop("/webhooks/{webhookId}/test")
    head["paths"]["/hooks/{webhookId}/test"] = operation
    report = run_case(tmp_path, head)
    changes = [
        item
        for item in report.diagnostics
        if item.code == "DEPENDENCY_CHANGED" and item.affected_steps[0].step_id == "sendTest"
    ]
    assert changes
    assert "/path" in changes[0].details["change"]["changedPaths"]
    assert report.summary()["errors"] == 0


def test_external_ref_is_unknown_and_never_fetched(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["components"]["schemas"]["WebhookSubscription"]["properties"]["eventTypes"]["items"] = {
        "$ref": "https://example.test/schemas/event-type.yaml"
    }
    report = run_case(tmp_path, head)
    external = [item for item in report.diagnostics if item.code == "UNSUPPORTED_EXTERNAL_REF"]
    assert external
    assert all(item.severity == "unknown" for item in external)
    assert report.summary()["errors"] == 0


def test_unresolved_oas_ref_has_error_code_and_source_pointer(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["paths"]["/webhooks"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
        "$ref": "#/components/schemas/DoesNotExist"
    }
    report = run_case(tmp_path, head)
    diagnostics = [item for item in report.diagnostics if item.code == "OAS_REF_UNRESOLVED"]
    assert diagnostics
    assert diagnostics[0].source_pointer.endswith("/schema/$ref")
    assert report.summary()["errors"] >= 1


def test_unresolved_arazzo_ref_has_error_code_and_source_pointer(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["x-invalid-ref"] = {"$ref": "#/workflows/99"}
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    diagnostics = [item for item in report.diagnostics if item.code == "ARAZZO_REF_UNRESOLVED"]
    assert diagnostics
    assert diagnostics[0].source_pointer == "/x-invalid-ref/$ref"
    assert report.summary()["errors"] >= 1


def test_missing_security_scheme_is_a_deterministic_error(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["paths"]["/webhooks/{webhookId}/test"]["post"]["security"] = [{"missingScheme": []}]
    report = run_case(tmp_path, head)
    diagnostics = [item for item in report.diagnostics if item.code == "SECURITY_SCHEME_MISSING"]
    assert len(diagnostics) == 1
    assert diagnostics[0].affected_steps[0].step_id == "sendTest"
    assert report.summary()["errors"] >= 1


def test_dynamic_payload_is_not_validated(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][0]["requestBody"]["payload"] = "$inputs.subscription"
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    dynamic = [item for item in report.diagnostics if item.code == "DYNAMIC_PAYLOAD_UNCHECKED"]
    assert len(dynamic) == 1
    assert dynamic[0].severity == "unknown"
    assert report.summary()["errors"] == 0


def test_official_response_runtime_expressions_are_supported(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    steps = workflow["workflows"][0]["steps"]
    steps[0]["outputs"]["webhookId"] = "$response.body"
    steps[1]["outputs"]["deliveryId"] = "$response.header.X-Request-Id"
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert not any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


def test_nonstandard_response_headers_expression_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][0]["outputs"]["webhookId"] = "$response.headers.id"
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


@pytest.mark.parametrize("expression", ["$outputs.foo", "$components.foo"])
def test_unsupported_runtime_expression_namespace_is_unknown(
    source_documents, tmp_path, expression
):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][1]["parameters"][0]["value"] = expression
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert any(
        item.code == "UNSUPPORTED_ARAZZO_FEATURE" and item.severity == "unknown"
        for item in report.diagnostics
    )


def test_selector_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][1]["requestBody"]["selector"] = "$inputs.selector"
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


def test_non_string_output_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][0]["outputs"]["webhookId"] = {"value": "id"}
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


def test_parameter_ref_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][1]["parameters"][0] = {
        "$ref": "#/components/parameters/WebhookId"
    }
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


def test_reusable_request_body_ref_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][1]["requestBody"] = {
        "$ref": "#/components/requestBodies/TestEvent"
    }
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


def test_non_json_request_body_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    head = copy.deepcopy(head)
    head["paths"]["/webhooks/{webhookId}/test"]["post"]["requestBody"]["content"] = {
        "text/plain": {"schema": {"type": "string"}}
    }
    report = run_case(tmp_path, head, copy.deepcopy(workflow))
    assert any(item.code == "UNSUPPORTED_ARAZZO_FEATURE" for item in report.diagnostics)


def test_unsupported_arazzo_feature_is_unknown(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["workflows"][0]["steps"][0]["successCriteria"] = [{"condition": "$statusCode == 201"}]
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    diagnostics = [item for item in report.diagnostics if item.code == "UNSUPPORTED_ARAZZO_FEATURE"]
    assert diagnostics
    assert all(item.severity == "unknown" for item in diagnostics)
    assert report.summary()["errors"] == 0


def test_arazzo_requires_1_1_x_and_one_openapi_source(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    workflow["arazzo"] = "1.0.0"
    with pytest.raises(InputError):
        run_case(tmp_path, copy.deepcopy(head), workflow)

    workflow["arazzo"] = "1.1.0"
    workflow["sourceDescriptions"].append(copy.deepcopy(workflow["sourceDescriptions"][0]))
    with pytest.raises(InputError):
        run_case(tmp_path, copy.deepcopy(head), workflow)

    workflow["sourceDescriptions"] = [workflow["sourceDescriptions"][0]]
    workflow["sourceDescriptions"][0]["url"] = ""
    with pytest.raises(InputError):
        run_case(tmp_path, copy.deepcopy(head), workflow)

    workflow["sourceDescriptions"][0]["url"] = "./openapi.yaml"
    workflow["sourceDescriptions"][0]["name"] = "webhooks.invalid"
    with pytest.raises(InputError):
        run_case(tmp_path, copy.deepcopy(head), workflow)


def test_plain_operation_ids_are_supported(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    for step in workflow["workflows"][0]["steps"]:
        step["operationId"] = step["operationId"].rsplit(".", 1)[-1]
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    assert not any(item.code == "OAS_OPERATION_MISSING" for item in report.diagnostics)
    assert report.summary()["errors"] == 0


def test_ref_depth_limit_is_enforced_with_cli_exit_two(source_documents, tmp_path, capsys):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    schemas = head["components"]["schemas"]
    for number in range(MAX_REF_DEPTH + 1):
        schemas[f"Deep{number}"] = {"$ref": f"#/components/schemas/Deep{number + 1}"}
    schemas[f"Deep{MAX_REF_DEPTH + 1}"] = {"type": "string"}
    head["paths"]["/webhooks"]["post"]["requestBody"]["content"]["application/json"]["schema"] = {
        "$ref": "#/components/schemas/Deep0"
    }
    base_path, head_path, workflow_path = write_case(tmp_path, head)
    assert (
        main(
            [
                "check",
                "--base-openapi",
                str(base_path),
                "--head-openapi",
                str(head_path),
                "--arazzo",
                str(workflow_path),
            ]
        )
        == 2
    )
    assert "reference depth exceeds" in capsys.readouterr().err


def test_missing_output_and_dependency_cycle_are_errors(source_documents, tmp_path):
    _, head, workflow = source_documents
    workflow = copy.deepcopy(workflow)
    steps = workflow["workflows"][0]["steps"]
    steps[1]["parameters"][0]["value"] = "$steps.createSubscription.outputs.missing"
    steps[0]["dependsOn"] = ["sendTest"]
    steps[1]["dependsOn"] = ["createSubscription"]
    report = run_case(tmp_path, copy.deepcopy(head), workflow)
    codes = {item.code for item in report.diagnostics}
    assert "ARAZZO_STEP_OUTPUT_MISSING" in codes
    assert "ARAZZO_DEPENDENCY_CYCLE" in codes
    assert report.summary()["errors"] >= 2


def test_duplicate_operation_id_blocks_binding(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["paths"]["/health"]["get"]["operationId"] = "sendTestEvent"
    report = run_case(tmp_path, head)
    assert "OAS_OPERATION_AMBIGUOUS" in {item.code for item in report.diagnostics}
    assert report.summary()["errors"] >= 1


def test_cli_json_and_markdown_are_stable_and_exit_zero(tmp_path, capsys):
    args = [
        "check",
        "--base-openapi",
        str(BASE_OPENAPI),
        "--head-openapi",
        str(HEAD_OPENAPI),
        "--arazzo",
        str(WORKFLOW),
        "--format",
        "json",
    ]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert json.loads(first)["schemaVersion"] == "0.1"
    assert main(args) == 0
    second = capsys.readouterr().out
    assert first == second

    assert main([*args[:-2], "--format", "markdown"]) == 0
    markdown = capsys.readouterr().out
    assert "Procedure CI impact report" in markdown
    assert "未检测到受影响" in markdown


def test_cli_input_failure_uses_exit_code_two(tmp_path, capsys):
    code = main(
        [
            "check",
            "--base-openapi",
            str(tmp_path / "missing.yaml"),
            "--head-openapi",
            str(HEAD_OPENAPI),
            "--arazzo",
            str(WORKFLOW),
        ]
    )
    assert code == 2
    assert "does not exist" in capsys.readouterr().err


def test_yaml_12_scalar_is_not_coerced_and_unknown_tag_is_rejected(tmp_path):
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("value: on\n", encoding="utf-8")
    assert load_document(scalar).data["value"] == "on"

    tagged = tmp_path / "tagged.yaml"
    tagged.write_text("value: !include other.yaml\n", encoding="utf-8")
    with pytest.raises(InputError):
        load_document(tagged)


def test_cyclic_internal_schema_refs_are_bounded(source_documents, tmp_path):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["components"]["schemas"]["CycleA"] = {"$ref": "#/components/schemas/CycleB"}
    head["components"]["schemas"]["CycleB"] = {"$ref": "#/components/schemas/CycleA"}
    head["paths"]["/webhooks/{webhookId}/deliveries/{deliveryId}"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"] = {"$ref": "#/components/schemas/CycleA"}
    base_path, head_path, _ = write_case(tmp_path, head)
    index = build_oas_index(load_document(head_path))
    operation = index.operation("getWebhookDelivery")
    assert operation is not None
    assert "schema:CycleA" in operation.dependency_keys
    assert "schema:CycleB" in operation.dependency_keys
    # The report must still be produced even though the dependency graph is cyclic.
    report = analyze(base_path, head_path, WORKFLOW)
    assert report.summary()["errors"] == 0


@pytest.mark.parametrize("feature", ["$dynamicRef", "$anchor", "$id"])
def test_unsupported_oas_reference_features_are_unknown(source_documents, tmp_path, feature):
    _, head, _ = source_documents
    head = copy.deepcopy(head)
    head["components"]["schemas"]["Subscription"][feature] = "urn:procedure-ci:feature"
    report = run_case(tmp_path, head)
    assert any(
        item.code == "UNSUPPORTED_OAS_FEATURE" and item.severity == "unknown"
        for item in report.diagnostics
    )
