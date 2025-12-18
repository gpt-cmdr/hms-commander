#!/usr/bin/env python
"""
Generate condensed output digests from executed Jupyter notebooks.

Usage:
    python audit_ipynb.py notebook.ipynb [--out-dir DIR]
    python audit_ipynb.py notebook.ipynb --pytest-log pytest.log --out-dir DIR

Output:
    audit.md - Human-readable summary
    audit.json - Machine-readable data

Purpose:
    Create small "digest" files from notebooks for downstream review by:
    - notebook-output-auditor (Haiku) - Find exceptions/errors
    - notebook-anomaly-spotter (Haiku) - Find unexpected behavior

    Avoids sending entire notebook JSON to Haiku agents.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def parse_notebook(notebook_path: Path) -> Dict[str, Any]:
    """
    Parse Jupyter notebook JSON.

    Args:
        notebook_path: Path to .ipynb file

    Returns:
        Notebook data dictionary
    """
    with open(notebook_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_cell_outputs(notebook: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract cell execution outputs from notebook.

    Args:
        notebook: Notebook data dictionary

    Returns:
        List of cell output summaries
    """
    cell_outputs = []

    for idx, cell in enumerate(notebook.get('cells', [])):
        cell_type = cell.get('cell_type', 'unknown')
        source = ''.join(cell.get('source', []))

        cell_data = {
            'index': idx,
            'cell_type': cell_type,
            'source': source[:500],  # Truncate long source
            'has_output': False,
            'output_types': [],
            'outputs': []
        }

        # Extract outputs for code cells
        if cell_type == 'code':
            outputs = cell.get('outputs', [])

            if outputs:
                cell_data['has_output'] = True

                for output in outputs:
                    output_type = output.get('output_type', 'unknown')
                    cell_data['output_types'].append(output_type)

                    # Extract different output types
                    if output_type == 'error':
                        # Exception/traceback
                        cell_data['outputs'].append({
                            'type': 'error',
                            'ename': output.get('ename', ''),
                            'evalue': output.get('evalue', ''),
                            'traceback': output.get('traceback', [])
                        })

                    elif output_type == 'stream':
                        # stdout/stderr
                        stream_name = output.get('name', 'stdout')
                        text = ''.join(output.get('text', []))
                        cell_data['outputs'].append({
                            'type': 'stream',
                            'name': stream_name,
                            'text': text[:1000]  # Truncate long output
                        })

                    elif output_type in ['execute_result', 'display_data']:
                        # Display outputs (DataFrames, plots, etc.)
                        data = output.get('data', {})

                        # Extract text/plain representation
                        text_repr = data.get('text/plain', '')
                        if isinstance(text_repr, list):
                            text_repr = ''.join(text_repr)

                        cell_data['outputs'].append({
                            'type': output_type,
                            'text': text_repr[:1000],  # Truncate
                            'has_image': 'image/png' in data,
                            'has_html': 'text/html' in data
                        })

        cell_outputs.append(cell_data)

    return cell_outputs


def summarize_notebook(notebook: Dict[str, Any], cell_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for notebook.

    Args:
        notebook: Notebook data dictionary
        cell_outputs: Extracted cell outputs

    Returns:
        Summary statistics
    """
    total_cells = len(cell_outputs)
    code_cells = sum(1 for c in cell_outputs if c['cell_type'] == 'code')
    markdown_cells = sum(1 for c in cell_outputs if c['cell_type'] == 'markdown')

    cells_with_output = sum(1 for c in cell_outputs if c['has_output'])
    cells_with_errors = sum(1 for c in cell_outputs
                           if 'error' in c['output_types'])

    return {
        'total_cells': total_cells,
        'code_cells': code_cells,
        'markdown_cells': markdown_cells,
        'cells_with_output': cells_with_output,
        'cells_with_errors': cells_with_errors
    }


def find_cells_with_issues(cell_outputs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find cells with errors or potential issues.

    Args:
        cell_outputs: Extracted cell outputs

    Returns:
        Dictionary of issue categories and affected cells
    """
    issues = {
        'errors': [],
        'stderr': [],
        'empty_results': [],
        'suspicious': []
    }

    for cell in cell_outputs:
        # Errors/exceptions
        if 'error' in cell['output_types']:
            issues['errors'].append(cell)

        # stderr output
        for output in cell.get('outputs', []):
            if output.get('type') == 'stream' and output.get('name') == 'stderr':
                issues['stderr'].append({
                    'cell': cell,
                    'stderr_text': output.get('text', '')
                })

        # Empty results (basic detection)
        for output in cell.get('outputs', []):
            text = output.get('text', '')
            if any(pattern in text.lower() for pattern in
                   ['empty dataframe', '0 rows', 'index: []', 'length: 0']):
                issues['empty_results'].append({
                    'cell': cell,
                    'output_text': text
                })

        # Suspicious patterns (basic detection)
        for output in cell.get('outputs', []):
            text = output.get('text', '')
            if any(pattern in text.lower() for pattern in
                   ['nan', 'inf', 'min       0.0', 'max       0.0']):
                issues['suspicious'].append({
                    'cell': cell,
                    'output_text': text,
                    'pattern': 'suspicious_values'
                })

    return issues


def generate_markdown_digest(
    notebook_path: Path,
    summary: Dict[str, Any],
    cell_outputs: List[Dict[str, Any]],
    issues: Dict[str, List[Any]],
    pytest_log: Optional[str] = None
) -> str:
    """
    Generate human-readable markdown digest.

    Args:
        notebook_path: Path to notebook
        summary: Summary statistics
        cell_outputs: Cell outputs
        issues: Detected issues
        pytest_log: Optional pytest log content

    Returns:
        Markdown string
    """
    lines = [
        f"# Notebook Audit: {notebook_path.name}",
        "",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        f"- Total cells: {summary['total_cells']}",
        f"- Code cells: {summary['code_cells']}",
        f"- Markdown cells: {summary['markdown_cells']}",
        f"- Cells with output: {summary['cells_with_output']}",
        f"- Cells with errors: {summary['cells_with_errors']}",
        ""
    ]

    # Pytest log summary
    if pytest_log:
        lines.extend([
            "## Pytest Execution",
            "",
            "```",
            pytest_log[-500:] if len(pytest_log) > 500 else pytest_log,  # Last 500 chars
            "```",
            ""
        ])

    # Cells with errors
    if issues['errors']:
        lines.extend([
            "## Cells with Errors",
            ""
        ])

        for cell in issues['errors']:
            lines.append(f"### Cell {cell['index']} (code)")
            lines.append("")
            lines.append("**Source**:")
            lines.append("```python")
            lines.append(cell['source'][:300])  # Truncate long source
            lines.append("```")
            lines.append("")

            # Extract error output
            for output in cell['outputs']:
                if output.get('type') == 'error':
                    lines.append("**Error**:")
                    lines.append("```")
                    lines.append(f"{output['ename']}: {output['evalue']}")
                    if output.get('traceback'):
                        lines.extend(output['traceback'][:10])  # First 10 lines
                    lines.append("```")
                    lines.append("")

    # stderr output
    if issues['stderr']:
        lines.extend([
            "## stderr Output",
            ""
        ])

        for item in issues['stderr']:
            lines.append(f"### Cell {item['cell']['index']}")
            lines.append("```")
            lines.append(item['stderr_text'][:500])  # Truncate
            lines.append("```")
            lines.append("")

    # Empty results
    if issues['empty_results']:
        lines.extend([
            "## Potential Empty Results",
            ""
        ])

        for item in issues['empty_results']:
            lines.append(f"### Cell {item['cell']['index']}")
            lines.append("```")
            lines.append(item['output_text'][:300])
            lines.append("```")
            lines.append("")

    # Suspicious patterns
    if issues['suspicious']:
        lines.extend([
            "## Suspicious Patterns",
            ""
        ])

        for item in issues['suspicious']:
            lines.append(f"### Cell {item['cell']['index']} ({item.get('pattern', 'unknown')})")
            lines.append("```")
            lines.append(item['output_text'][:300])
            lines.append("```")
            lines.append("")

    # Sample outputs (if no issues)
    if not any(issues.values()):
        lines.extend([
            "## Status: CLEAN",
            "",
            "No errors, stderr, or obvious anomalies detected.",
            "",
            "### Sample Outputs",
            ""
        ])

        # Show first few cells with output
        output_cells = [c for c in cell_outputs if c['has_output']][:3]
        for cell in output_cells:
            lines.append(f"### Cell {cell['index']} (code)")
            lines.append("")

            for output in cell['outputs']:
                if output.get('type') in ['stream', 'execute_result', 'display_data']:
                    text = output.get('text', '')
                    if text:
                        lines.append("```")
                        lines.append(text[:200])  # Small sample
                        lines.append("```")
                        lines.append("")

    return '\n'.join(lines)


def generate_json_digest(
    notebook_path: Path,
    summary: Dict[str, Any],
    cell_outputs: List[Dict[str, Any]],
    issues: Dict[str, List[Any]]
) -> Dict[str, Any]:
    """
    Generate machine-readable JSON digest.

    Args:
        notebook_path: Path to notebook
        summary: Summary statistics
        cell_outputs: Cell outputs
        issues: Detected issues

    Returns:
        Digest dictionary
    """
    return {
        'notebook': str(notebook_path),
        'generated': datetime.now().isoformat(),
        'summary': summary,
        'issues': {
            'error_count': len(issues['errors']),
            'stderr_count': len(issues['stderr']),
            'empty_result_count': len(issues['empty_results']),
            'suspicious_count': len(issues['suspicious']),
            'error_cells': [c['index'] for c in issues['errors']],
            'stderr_cells': [item['cell']['index'] for item in issues['stderr']],
        },
        'cell_outputs': cell_outputs  # Full cell data for programmatic access
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    notebook_path = Path(sys.argv[1])

    if not notebook_path.exists():
        print(f"Error: Notebook not found: {notebook_path}")
        sys.exit(1)

    # Parse arguments
    out_dir = Path.cwd()
    pytest_log = None

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--out-dir':
            out_dir = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--pytest-log':
            pytest_log_path = Path(sys.argv[i + 1])
            if pytest_log_path.exists():
                with open(pytest_log_path, 'r', encoding='utf-8') as f:
                    pytest_log = f.read()
            i += 2
        else:
            i += 1

    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse notebook
    print(f"Parsing notebook: {notebook_path}")
    notebook = parse_notebook(notebook_path)

    # Extract outputs
    print("Extracting cell outputs...")
    cell_outputs = extract_cell_outputs(notebook)

    # Generate summary
    print("Generating summary...")
    summary = summarize_notebook(notebook, cell_outputs)

    # Find issues
    print("Detecting issues...")
    issues = find_cells_with_issues(cell_outputs)

    # Generate digests
    print("Generating digests...")

    # Markdown
    md_content = generate_markdown_digest(
        notebook_path, summary, cell_outputs, issues, pytest_log
    )
    md_path = out_dir / 'audit.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"  Created: {md_path}")

    # JSON
    json_data = generate_json_digest(
        notebook_path, summary, cell_outputs, issues
    )
    json_path = out_dir / 'audit.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    print(f"  Created: {json_path}")

    # Summary
    print("\nSummary:")
    print(f"  Total cells: {summary['total_cells']}")
    print(f"  Errors found: {len(issues['errors'])}")
    print(f"  stderr outputs: {len(issues['stderr'])}")
    print(f"  Empty results: {len(issues['empty_results'])}")
    print(f"  Suspicious patterns: {len(issues['suspicious'])}")

    # Exit code
    if issues['errors']:
        print("\n[!] Notebook has errors")
        sys.exit(1)
    else:
        print("\n[OK] Notebook appears clean")
        sys.exit(0)


if __name__ == '__main__':
    main()
