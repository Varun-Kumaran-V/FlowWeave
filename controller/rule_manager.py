
class RuleManager:
    def __init__(self, switch_connection):
        self.sw = switch_connection

    def install_rule(self, rule_params):
        """
        Constructs and writes a P4 Table Entry.
        """
        # Mocking the P4Runtime Write operation
        # In production: table_entry = p4runtime_sh.TableEntry(rule_params['table'])...
        
        print(f"[RuleMgr] WRITING TABLE ENTRY -> Table: {rule_params['table']} | "
              f"Match: {rule_params['dst_ip']}/{rule_params['mask']} | "
              f"Action: {rule_params['action']}")
        return True

    def delete_rule(self, prefix_key):
        """
        Deletes a rule based on the key.
        """
        print(f"[RuleMgr] DELETING TABLE ENTRY -> Match: {prefix_key}")
        return True