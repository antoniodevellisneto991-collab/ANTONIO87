"""
Google Cloud Organization Policies — Delete operations.
Wraps the gcloud org-policies delete functionality using the Python client library.

Equivalent CLI:
    gcloud org-policies delete CONSTRAINT_NAME --organization=ORGANIZATION_ID
    gcloud org-policies delete CONSTRAINT_NAME --project=PROJECT_ID
    gcloud org-policies delete CONSTRAINT_NAME --folder=FOLDER_ID
"""

from google.cloud import orgpolicy_v2


_client = None


def get_client() -> orgpolicy_v2.OrgPolicyClient:
    """Lazy-initialize the Organization Policy client."""
    global _client
    if _client is None:
        _client = orgpolicy_v2.OrgPolicyClient()
    return _client


def _build_policy_name(constraint: str, organization: str = None,
                       project: str = None, folder: str = None) -> str:
    """Build the fully-qualified policy resource name.

    Returns a name like:
        organizations/123456/policies/compute.disableSerialPortAccess
        projects/my-project/policies/compute.disableSerialPortAccess
        folders/789/policies/compute.disableSerialPortAccess
    """
    # Strip common prefixes so callers can pass either form
    constraint_id = constraint.removeprefix("constraints/")

    if organization:
        return f"organizations/{organization}/policies/{constraint_id}"
    elif project:
        return f"projects/{project}/policies/{constraint_id}"
    elif folder:
        return f"folders/{folder}/policies/{constraint_id}"
    else:
        raise ValueError(
            "One of organization, project, or folder must be provided."
        )


def delete_org_policy(constraint: str, organization: str = None,
                      project: str = None, folder: str = None) -> dict:
    """Delete an organization policy for a given constraint.

    Args:
        constraint: The constraint name (e.g. "compute.disableSerialPortAccess"
                    or "constraints/compute.disableSerialPortAccess").
        organization: Organization ID (e.g. "123456789").
        project: Project ID (e.g. "my-project").
        folder: Folder ID (e.g. "456789").

    Returns:
        A dict with the deletion result.

    Raises:
        ValueError: If no parent resource is specified.
        google.api_core.exceptions.NotFound: If the policy does not exist.
        google.api_core.exceptions.PermissionDenied: If credentials lack access.
    """
    policy_name = _build_policy_name(constraint, organization, project, folder)
    client = get_client()

    request = orgpolicy_v2.DeletePolicyRequest(name=policy_name)
    client.delete_policy(request=request)

    return {
        "deleted": True,
        "policy_name": policy_name,
        "constraint": constraint,
    }


def get_org_policy(constraint: str, organization: str = None,
                   project: str = None, folder: str = None) -> dict:
    """Retrieve an organization policy to verify it exists before deletion.

    Args:
        constraint: The constraint name.
        organization: Organization ID.
        project: Project ID.
        folder: Folder ID.

    Returns:
        A dict with policy details.
    """
    policy_name = _build_policy_name(constraint, organization, project, folder)
    client = get_client()

    request = orgpolicy_v2.GetPolicyRequest(name=policy_name)
    policy = client.get_policy(request=request)

    spec = policy.spec
    rules = []
    if spec and spec.rules:
        for rule in spec.rules:
            rule_info = {}
            if rule.enforce is not None:
                rule_info["enforce"] = rule.enforce
            if rule.allow_all is not None:
                rule_info["allow_all"] = rule.allow_all
            if rule.deny_all is not None:
                rule_info["deny_all"] = rule.deny_all
            if rule.condition:
                rule_info["condition"] = rule.condition.expression
            rules.append(rule_info)

    return {
        "name": policy.name,
        "constraint": constraint,
        "rules": rules,
        "update_time": str(policy.spec.update_time) if spec else None,
    }


def list_org_policies(organization: str = None, project: str = None,
                      folder: str = None) -> list[dict]:
    """List all organization policies for a given parent resource.

    Args:
        organization: Organization ID.
        project: Project ID.
        folder: Folder ID.

    Returns:
        A list of dicts with policy summaries.
    """
    if organization:
        parent = f"organizations/{organization}"
    elif project:
        parent = f"projects/{project}"
    elif folder:
        parent = f"folders/{folder}"
    else:
        raise ValueError(
            "One of organization, project, or folder must be provided."
        )

    client = get_client()
    request = orgpolicy_v2.ListPoliciesRequest(parent=parent)
    policies = client.list_policies(request=request)

    results = []
    for policy in policies:
        constraint_id = policy.name.rsplit("/policies/", 1)[-1]
        results.append({
            "name": policy.name,
            "constraint": constraint_id,
        })

    return results
