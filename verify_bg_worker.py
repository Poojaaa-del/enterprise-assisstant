#!/usr/bin/env python3
"""
Quick verification script to check if background worker exception handling is working.
This simulates the background worker flow without actually running the server.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def verify_document_parser():
    """Check that DocumentParserAgent.parse() accepts required parameters"""
    from agents.document_parser import DocumentParserAgent
    import inspect
    
    parser = DocumentParserAgent()
    sig = inspect.signature(parser.parse)
    params = list(sig.parameters.keys())
    
    print("✓ DocumentParserAgent.parse() signature:")
    print(f"  Parameters: {params}")
    
    required = ['file_bytes', 'filename', 'user_id', 'department', 'permitted_role']
    missing = [p for p in required if p not in params]
    
    if missing:
        print(f"✗ Missing required parameters: {missing}")
        return False
    else:
        print(f"✓ All required parameters present: {required}")
        return True


def verify_bg_process_file():
    """Check that _bg_process_file has proper error handling"""
    import ast
    
    with open('backend/api/knowledge.py', 'r', encoding='utf-8') as f:
        source = f.read()
    
    # Check for key error handling patterns
    checks = {
        'Has try-except in _bg_process_file': 'except Exception as exc:' in source and '[BACKGROUND WORKER ERROR]' in source,
        'Calls parser with user_id': 'parser.parse(' in source and 'user_id,' in source,
        'Calls parser with permitted_role': 'permitted_role=permitted_role' in source,
        'Updates job status': '_update_job_status' in source,
        'Commits to knowledge_files table': 'INSERT INTO knowledge_files' in source,
        'Includes file_hash in metadata': 'file_hash' in source,
    }
    
    print("\n✓ Background Worker (_bg_process_file) checks:")
    all_pass = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
        if not result:
            all_pass = False
    
    return all_pass


def verify_upload_endpoint():
    """Check that /upload endpoint schedules background tasks correctly"""
    with open('backend/api/knowledge.py', 'r', encoding='utf-8') as f:
        source = f.read()
    
    checks = {
        'Creates ingestion_jobs record': 'INSERT INTO ingestion_jobs' in source,
        'Schedules background_tasks.add_task': 'background_tasks.add_task' in source,
        'Passes user_id to worker': '_bg_process_file' in source and 'current_user.id' in source,
        'Returns 202 Accepted status': 'status_code=202' in source or 'status_code': 202,
    }
    
    print("\n✓ Upload Endpoint checks:")
    all_pass = True
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
        if not result:
            all_pass = False
    
    return all_pass


if __name__ == "__main__":
    print("=" * 70)
    print("BACKGROUND WORKER VERIFICATION")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("DocumentParserAgent", verify_document_parser()))
    except Exception as e:
        print(f"✗ DocumentParserAgent check failed: {e}")
        results.append(("DocumentParserAgent", False))
    
    try:
        results.append(("Background Worker", verify_bg_process_file()))
    except Exception as e:
        print(f"✗ Background Worker check failed: {e}")
        results.append(("Background Worker", False))
    
    try:
        results.append(("Upload Endpoint", verify_upload_endpoint()))
    except Exception as e:
        print(f"✗ Upload Endpoint check failed: {e}")
        results.append(("Upload Endpoint", False))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_passed = all(result[1] for result in results)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    print("=" * 70)
    
    if all_passed:
        print("✓ ALL CHECKS PASSED - Background worker is properly configured!")
        sys.exit(0)
    else:
        print("✗ SOME CHECKS FAILED - Review the output above")
        sys.exit(1)
