import json
from pathlib import Path

from roboarc.contracts import WorkflowDocument
from roboarc.runtime.registry import CapabilityRegistry
from roboarc.runtime.validation import validate_workflow
from roboarc_tiago.profile import TIAGO_MANIFESTS, TIAGO_PROFILE

ROOT = Path(__file__).parents[2]


def _load(name: str) -> WorkflowDocument:
    return WorkflowDocument.model_validate(
        json.loads((ROOT / "examples/workflows" / name).read_text())
    )


def test_community_fixtures_use_tiago_profile_and_supported_nodes() -> None:
    refs = {(item.id, item.version) for item in TIAGO_MANIFESTS}
    registry = CapabilityRegistry(TIAGO_PROFILE, TIAGO_MANIFESTS)
    for name in ("tiago-reception-greeting.json", "tiago-look-and-say.json"):
        workflow = _load(name)
        assert workflow.profile_id == TIAGO_PROFILE.id
        report = validate_workflow(workflow, registry)
        assert report.valid, report.issues

        def visit(node):
            if node.type == "sequence":
                for child in node.children:
                    yield from visit(child)
            elif node.type == "wait":
                assert node.duration_ms > 0
            else:
                assert (node.capability.id, node.capability.version) in refs

        list(visit(workflow.workflow))


def test_user_composition_is_reordered_and_argument_changed() -> None:
    fixture = _load("tiago-reception-greeting.json")
    children = list(fixture.workflow.children)
    user_children = [children[2], children[0], children[1]]
    user_children[0] = user_children[0].model_copy(
        update={"args": {"text": "Hello from the community workspace."}}
    )
    assert [child.id for child in user_children] != [child.id for child in children]
    assert user_children[0].args["text"] != children[2].args["text"]


def test_local_extension_is_discoverable_and_validated() -> None:
    registry = CapabilityRegistry(TIAGO_PROFILE, TIAGO_MANIFESTS)
    extension = registry.require(type(TIAGO_PROFILE.capabilities[0])(id="community.say", version=1))
    assert extension.category == "Community"
    workflow = _load("tiago-look-and-say.json").model_copy(
        update={"workflow": _load("tiago-look-and-say.json").workflow.model_copy(update={
            "children": [extension_workflow_node()]
        })}
    )
    report = validate_workflow(workflow, registry)
    assert report.valid


def extension_workflow_node():
    from roboarc.contracts import CapabilityNode

    return CapabilityNode(
        id="community-say",
        capability={"id": "community.say", "version": 1},
        args={"text": "extension smoke"},
    )
