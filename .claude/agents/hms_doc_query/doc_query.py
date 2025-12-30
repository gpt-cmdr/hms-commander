"""
HMS Documentation Query Agent

Query official HEC-HMS documentation to answer technical questions about
HMS features, methods, file formats, and workflows.

Usage:
    from hms_agents.HMS_DocQuery import query_documentation

    result = query_documentation(
        "What parameters does SCS Curve Number require?",
        focus_area="loss_methods"
    )
    print(result.answer)

Author: hms-commander
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys

# Flexible import for development vs installed package
try:
    from hms_commander._constants import (
        LOSS_METHODS,
        TRANSFORM_METHODS,
        BASEFLOW_METHODS,
        ROUTING_METHODS,
        PRECIP_METHODS,
        ET_METHODS,
        SNOWMELT_METHODS
    )
except ImportError:
    current_file = Path(__file__).resolve()
    parent_directory = current_file.parent.parent.parent
    sys.path.insert(0, str(parent_directory))
    from hms_commander._constants import (
        LOSS_METHODS,
        TRANSFORM_METHODS,
        BASEFLOW_METHODS,
        ROUTING_METHODS,
        PRECIP_METHODS,
        ET_METHODS,
        SNOWMELT_METHODS
    )


# Known HMS Documentation URLs
KNOWN_URLS = {
    # User's Manual (Confluence)
    "users_manual": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/",
    "users_manual_data": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/data-entry/",
    "users_manual_compute": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/computing-runs/",
    "users_manual_results": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmsum/latest/viewing-results/",

    # Technical Reference Manual (Confluence)
    "tech_ref": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/",
    "tech_ref_precip": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/meteorologic-models/precipitation/",
    "tech_ref_loss": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/basin-models/loss-methods/",
    "tech_ref_transform": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/basin-models/transform-methods/",
    "tech_ref_baseflow": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/basin-models/baseflow-methods/",
    "tech_ref_routing": "https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/latest/basin-models/routing-methods/",

    # Software and Downloads
    "downloads": "https://www.hec.usace.army.mil/software/hec-hms/downloads.aspx",
    "software_page": "https://www.hec.usace.army.mil/software/hec-hms/",

    # Release Notes (if available)
    "release_notes": "https://www.hec.usace.army.mil/software/hec-hms/documentation.aspx",

    # Community Resources
    "forum_kleinschmidt": "https://therassolution.kleinschmidtgroup.com/the-ras-solution-forum/",
    "forum_hydroschool": "https://hydroschool.org/forums/",
    "reddit_hecras": "https://www.reddit.com/r/HECRAS/",
    "cwms_resources": "https://www.hec.usace.army.mil/confluence/cwmsdocs/cmrkit/latest/online-resources-for-cwms-hec-rts",
}


@dataclass
class QueryResult:
    """Result from a documentation query."""

    question: str
    answer: str
    sources: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    confidence: str = "medium"  # low, medium, high
    method_validated: bool = False

    def __str__(self) -> str:
        """Format result for display."""
        output = []
        output.append(f"Question: {self.question}")
        output.append(f"\nAnswer:\n{self.answer}")

        if self.sources:
            output.append(f"\nSources:")
            for source in self.sources:
                output.append(f"  - {source}")

        if self.urls:
            output.append(f"\nRelevant URLs:")
            for url in self.urls:
                output.append(f"  - {url}")

        output.append(f"\nConfidence: {self.confidence}")

        return "\n".join(output)


@dataclass
class MethodParameters:
    """Parameters for an HMS method."""

    method_type: str  # loss, transform, baseflow, routing, precip, et
    method_name: str
    parameters: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # parameters structure: {param_name: {type, units, default, description}}

    hms_version: Optional[str] = None
    source_url: Optional[str] = None

    def get_required_params(self) -> List[str]:
        """Get list of required parameter names."""
        return [
            name for name, info in self.parameters.items()
            if info.get('required', True)
        ]

    def get_optional_params(self) -> List[str]:
        """Get list of optional parameter names."""
        return [
            name for name, info in self.parameters.items()
            if not info.get('required', True)
        ]


def validate_method_name(
    method_name: str,
    method_type: str,
    hms_version: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if a method name is valid in HMS.

    Args:
        method_name: Method name to validate
        method_type: Type of method (loss, transform, baseflow, routing, precip, et, snowmelt)
        hms_version: Target HMS version (optional)

    Returns:
        Tuple of (is_valid, suggestion)
        - is_valid: True if exact match found
        - suggestion: Closest match if not exact, None if exact match
    """
    # Get the appropriate method list
    method_lists = {
        'loss': LOSS_METHODS,
        'transform': TRANSFORM_METHODS,
        'baseflow': BASEFLOW_METHODS,
        'routing': ROUTING_METHODS,
        'precip': PRECIP_METHODS,
        'precipitation': PRECIP_METHODS,
        'et': ET_METHODS,
        'evapotranspiration': ET_METHODS,
        'snowmelt': SNOWMELT_METHODS
    }

    method_list = method_lists.get(method_type.lower())
    if not method_list:
        return False, None

    # Exact match (case-insensitive)
    if method_name in method_list:
        return True, None

    # Try case-insensitive match
    method_lower = method_name.lower()
    for method in method_list:
        if method.lower() == method_lower:
            return True, method  # Return correct case

    # Find closest match (simple substring matching)
    for method in method_list:
        if method_lower in method.lower() or method.lower() in method_lower:
            return False, method

    return False, None


def get_focus_area_url(focus_area: Optional[str]) -> List[str]:
    """
    Get relevant URLs based on focus area.

    Args:
        focus_area: Area to focus search (loss_methods, file_formats, etc.)

    Returns:
        List of relevant URLs
    """
    focus_mapping = {
        'loss_methods': ['tech_ref_loss', 'tech_ref'],
        'transform_methods': ['tech_ref_transform', 'tech_ref'],
        'baseflow_methods': ['tech_ref_baseflow', 'tech_ref'],
        'routing_methods': ['tech_ref_routing', 'tech_ref'],
        'precip_methods': ['tech_ref_precip', 'tech_ref'],
        'precipitation': ['tech_ref_precip', 'tech_ref'],
        'file_formats': ['users_manual_data', 'users_manual'],
        'workflows': ['users_manual', 'users_manual_compute'],
        'release_notes': ['release_notes', 'downloads'],
        'installation': ['downloads', 'software_page'],
        'troubleshooting': ['users_manual', 'software_page'],
    }

    if not focus_area:
        return [KNOWN_URLS['users_manual'], KNOWN_URLS['tech_ref']]

    keys = focus_mapping.get(focus_area.lower(), ['users_manual', 'tech_ref'])
    return [KNOWN_URLS[key] for key in keys if key in KNOWN_URLS]


def query_documentation(
    question: str,
    focus_area: Optional[str] = None,
    hms_version: Optional[str] = None,
    verbose: bool = False,
    use_web_tools: bool = True
) -> QueryResult:
    """
    Query HEC-HMS documentation to answer a technical question.

    Uses WebFetch and WebSearch to retrieve and analyze official HEC-HMS documentation.

    IMPORTANT: Image Visibility Limitation
    While HEC-HMS documentation contains screenshots and diagrams, WebFetch currently
    retrieves only text content. Images are referenced but not rendered. The agent
    still provides useful answers from textual documentation, but cannot describe
    UI screenshots or visual diagrams.

    Args:
        question: The technical question to answer
        focus_area: Narrow search to specific area (optional)
        hms_version: Target HMS version (optional)
        verbose: Print search progress
        use_web_tools: If False, return URLs only without web queries

    Returns:
        QueryResult with answer, sources, and URLs

    Example:
        >>> result = query_documentation(
        ...     "What parameters does SCS Curve Number require?",
        ...     focus_area="loss_methods"
        ... )
        >>> print(result.answer)
    """
    if verbose:
        print(f"Querying HMS documentation...")
        print(f"  Question: {question}")
        if focus_area:
            print(f"  Focus area: {focus_area}")
        if hms_version:
            print(f"  HMS version: {hms_version}")

    # Get relevant URLs based on focus area
    urls = get_focus_area_url(focus_area)

    # If not using web tools, return URL guidance only
    if not use_web_tools:
        return QueryResult(
            question=question,
            answer=(
                f"For your question: '{question}'\n\n"
                f"Please consult these official HMS documentation URLs:\n" +
                "\n".join(f"  - {url}" for url in urls)
            ),
            sources=["HEC-HMS Documentation"],
            urls=urls,
            confidence="low"
        )

    # This function is designed to be called by Claude Code with WebFetch/WebSearch tools
    # When run in that context, Claude will make the actual web requests
    # When run standalone, provide structured response

    # Build search query
    search_query = f"HEC-HMS {question}"
    if focus_area:
        search_query += f" {focus_area.replace('_', ' ')}"
    if hms_version:
        search_query += f" version {hms_version}"

    result = QueryResult(
        question=question,
        answer=(
            f"To answer '{question}':\n\n"
            "This function should be called by Claude Code with WebFetch/WebSearch tools.\n"
            "In that context, Claude will:\n"
            "1. Use WebSearch to find relevant HMS documentation pages\n"
            "2. Use WebFetch to retrieve content from top results\n"
            "3. Extract relevant information from text content\n"
            "4. Synthesize an answer with citations\n\n"
            f"Search query: {search_query}\n\n"
            f"Recommended documentation URLs:\n" +
            "\n".join(f"  - {url}" for url in urls) +
            "\n\n"
            "Note: WebFetch retrieves text content but not embedded images/screenshots."
        ),
        sources=["HEC-HMS Official Documentation"],
        urls=urls,
        confidence="medium"
    )

    if verbose:
        print(f"  Search query: {search_query}")
        print(f"  Found {len(urls)} relevant documentation sources")

    return result


def get_method_parameters(
    method_type: str,
    method_name: str,
    hms_version: Optional[str] = None,
    verbose: bool = False
) -> Optional[MethodParameters]:
    """
    Get parameter details for a specific HMS method.

    Args:
        method_type: Type of method (loss, transform, baseflow, routing)
        method_name: Name of the method (e.g., "SCS Curve Number")
        hms_version: Target HMS version (optional)
        verbose: Print search progress

    Returns:
        MethodParameters object with parameter details, or None if not found
    """
    if verbose:
        print(f"Looking up parameters for {method_type} method: {method_name}")

    # Validate method name first
    is_valid, suggestion = validate_method_name(method_name, method_type, hms_version)

    if not is_valid:
        if verbose:
            if suggestion:
                print(f"  Method '{method_name}' not found. Did you mean '{suggestion}'?")
            else:
                print(f"  Method '{method_name}' not found in {method_type} methods.")
        return None

    # Use corrected name if suggestion provided
    if suggestion:
        method_name = suggestion
        if verbose:
            print(f"  Using method name: {method_name}")

    # This is a placeholder - actual implementation would fetch from documentation
    # For now, return a sample structure

    # Example for SCS Curve Number
    if method_name == "SCS Curve Number" and method_type.lower() == "loss":
        params = MethodParameters(
            method_type=method_type,
            method_name=method_name,
            parameters={
                "Initial Abstraction": {
                    "type": "float",
                    "units": "mm or in",
                    "default": "calculated from CN",
                    "description": "Initial abstraction before runoff begins",
                    "required": True
                },
                "Curve Number": {
                    "type": "float",
                    "units": "dimensionless",
                    "default": "None",
                    "description": "SCS Curve Number (0-100)",
                    "required": True
                },
                "Impervious": {
                    "type": "float",
                    "units": "%",
                    "default": "0",
                    "description": "Percent impervious area",
                    "required": False
                }
            },
            hms_version=hms_version,
            source_url=KNOWN_URLS.get('tech_ref_loss')
        )
        return params

    # Generic placeholder for other methods
    params = MethodParameters(
        method_type=method_type,
        method_name=method_name,
        parameters={},  # Would be populated from documentation
        hms_version=hms_version,
        source_url=get_focus_area_url(f"{method_type}_methods")[0]
    )

    if verbose:
        print(f"  Placeholder: Actual parameters would be fetched from documentation")

    return params


def search_release_notes(
    query: str,
    version: Optional[str] = None,
    verbose: bool = False
) -> List[Dict[str, str]]:
    """
    Search HMS release notes for version-specific information.

    Args:
        query: Search query
        version: Specific version to search (optional)
        verbose: Print search progress

    Returns:
        List of relevant release note entries
    """
    if verbose:
        print(f"Searching release notes for: {query}")
        if version:
            print(f"  Version filter: {version}")

    # Placeholder - would use WebFetch to get release notes
    results = [
        {
            "version": version or "4.11",
            "date": "2023-XX-XX",
            "description": "Placeholder: Release note entry would be extracted from actual documentation",
            "url": KNOWN_URLS.get('release_notes', '')
        }
    ]

    return results


if __name__ == "__main__":
    """
    Demo usage of the documentation query agent.
    """
    print("=" * 80)
    print("HMS Documentation Query Agent - Demo")
    print("=" * 80)

    # Example 1: Validate method name
    print("\n[Example 1] Validate method name")
    is_valid, suggestion = validate_method_name("SCS Curve Number", "loss")
    print(f"  Is 'SCS Curve Number' a valid loss method? {is_valid}")

    is_valid, suggestion = validate_method_name("scs curve number", "loss")
    print(f"  Is 'scs curve number' valid? {is_valid} (suggestion: {suggestion})")

    is_valid, suggestion = validate_method_name("InvalidMethod", "loss")
    print(f"  Is 'InvalidMethod' valid? {is_valid} (suggestion: {suggestion})")

    # Example 2: Get method parameters
    print("\n[Example 2] Get method parameters")
    params = get_method_parameters("loss", "SCS Curve Number", verbose=True)
    if params:
        print(f"  Method: {params.method_name}")
        print(f"  Required parameters: {params.get_required_params()}")
        print(f"  Optional parameters: {params.get_optional_params()}")

    # Example 3: Query documentation
    print("\n[Example 3] Query documentation")
    result = query_documentation(
        "What parameters does the Deficit and Constant loss method require?",
        focus_area="loss_methods",
        verbose=True
    )
    print(f"\n{result}")

    # Example 4: List all known methods
    print("\n[Example 4] List known HMS methods")
    print(f"  Loss methods ({len(LOSS_METHODS)}): {', '.join(LOSS_METHODS[:3])}...")
    print(f"  Transform methods ({len(TRANSFORM_METHODS)}): {', '.join(TRANSFORM_METHODS[:3])}...")
    print(f"  Routing methods ({len(ROUTING_METHODS)}): {', '.join(ROUTING_METHODS[:3])}...")

    print("\n" + "=" * 80)
    print("Note: This is a demonstration with placeholder implementations.")
    print("Actual WebFetch/WebSearch integration would be added for production use.")
    print("=" * 80)
