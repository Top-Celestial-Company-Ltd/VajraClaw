import os
import re
import yaml

class ATREngine:
    def __init__(self, rules_dir):
        self.rules_dir = rules_dir
        self.rules = []
        self.load_rules()

    def load_rules(self):
        if not os.path.exists(self.rules_dir):
            print(f"ATR Rules directory not found: {self.rules_dir}")
            return

        for filename in os.listdir(self.rules_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(self.rules_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        rule_data = yaml.safe_load(f)
                    
                    rule_id = rule_data.get("id", "UNKNOWN")
                    rule_name = rule_data.get("name", "Unnamed Rule")
                    detection = rule_data.get("detection", {})
                    
                    keywords = detection.get("keywords", [])
                    regex_patterns = detection.get("regex", [])
                    
                    compiled_regexes = []
                    for pattern in regex_patterns:
                        try:
                            # Compile regular expression
                            compiled_regexes.append(re.compile(pattern))
                        except re.error as e:
                            print(f"Failed to compile regex pattern '{pattern}' in rule {rule_id}: {e}")

                    self.rules.append({
                        "id": rule_id,
                        "name": rule_name,
                        "keywords": [kw.lower() for kw in keywords],
                        "regexes": compiled_regexes
                    })
                except Exception as e:
                    print(f"Error loading ATR rule {filename}: {e}")

        print(f"Loaded {len(self.rules)} ATR rules from {self.rules_dir}")

    def check_query(self, query: str) -> tuple[bool, str, str]:
        """
        Checks a query against all loaded ATR rules.
        Returns:
            (is_blocked, rule_id, rule_name)
        """
        if not query:
            return False, "", ""

        query_lower = query.lower()

        for rule in self.rules:
            # 1. Keyword check
            for kw in rule["keywords"]:
                if kw in query_lower:
                    return True, rule["id"], rule["name"]

            # 2. Regex check
            for rx in rule["regexes"]:
                if rx.search(query):
                    return True, rule["id"], rule["name"]

        return False, "", ""
