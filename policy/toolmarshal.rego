package toolmarshal

import rego.v1

default allow := false

allow if input.tool in data.agents[input.agent]
