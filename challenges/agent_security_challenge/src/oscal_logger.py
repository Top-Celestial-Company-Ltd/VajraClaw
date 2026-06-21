import json
import uuid
from datetime import datetime
import os
import sys

# Solve Windows cp950 console encoding issues
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class OscalLogger:
    def __init__(self, log_dir="logs", log_filename="oscal_audit.json"):
        self.log_dir = log_dir
        self.log_path = os.path.join(log_dir, log_filename)
        os.makedirs(self.log_dir, exist_ok=True)
        
    def log_violation(self, agent_id, violation_type, target, action_taken="Thread Panic (Process Terminated)"):
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Build standard NIST OSCAL assessment-results structure
        oscal_record = {
            "assessment-results": {
                "uuid": str(uuid.uuid4()),
                "metadata": {
                    "title": "DROS Agent Security Runtime Assessment Results",
                    "last-modified": timestamp,
                    "version": "1.0",
                    "oscal-version": "1.1.0"
                },
                "results": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": f"DROS Runtime Threat Mitigation: {violation_type}",
                        "description": f"DROS GuardVM intercepted an unauthorized Agent action.",
                        "start": timestamp,
                        "observations": [
                            {
                                "uuid": str(uuid.uuid4()),
                                "description": "L0 Physical Execution violation caught at FFI boundary",
                                "methods": ["FFI-Chokepoint-Verification"],
                                "subjects": [
                                    {
                                        "type": "agent",
                                        "uuid": str(uuid.uuid5(uuid.NAMESPACE_DNS, agent_id)),
                                        "title": agent_id
                                    }
                                ],
                                "relevant-evidence": [
                                    {
                                        "description": f"Attempted to access target scope/resource: {target}",
                                        "remarks": f"FFI boundary check failed. Action enforced: {action_taken}"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        
        # Append or write the log in JSON Lines / JSON array format.
        # For simplicity and ease of automated tools, we write a list of OSCAL results.
        records = []
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    if not isinstance(records, list):
                        records = []
            except Exception:
                records = []
                
        records.append(oscal_record)
        
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
            
        print(f"OSCAL Compliance Audit Log generated at: {self.log_path}")

# Quick sanity check
if __name__ == "__main__":
    logger = OscalLogger(log_dir="../logs")
    logger.log_violation("Finance_Auditor_Agent", "AST_SCOPE_VIOLATION", "/Enterprise/Secret_Flag.txt")
