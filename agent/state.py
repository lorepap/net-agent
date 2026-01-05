from typing import List, Dict, Any, Union
import operator

# Python 3.7 compat
class AgentState(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "intermediate_steps" not in self:
            self["intermediate_steps"] = []

