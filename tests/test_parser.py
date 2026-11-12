
from skillshift.agents.reference import extract_action

tests = {
    "JSON click": (
        '```json\n{"action":"click","bid":"169"}\n```',
        "click('169')"
    ),
    "JSON goto": (
        '```json\n{"action":"goto","url":"http://localhost:8080/dashboard/todos"}\n```',
        "goto('http://localhost:8080/dashboard/todos')"
    ),
    "JSON fill": (
        '```json\n{"action":"fill","bid":"15","value":"hello"}\n```',
        "fill('15', 'hello')"
    ),
    "Python action": (
        '```python\nclick("169")\n```',
        'click("169")'
    ),
    "Unquoted URL": (
        '```action\ngoto(http://localhost:8080/dashboard/todos)\n```',
        "goto('http://localhost:8080/dashboard/todos')"
    ),
}

for name, (text, expected) in tests.items():
    actual = extract_action(text)
    assert actual == expected, (
        f"{name}: expected={expected!r}, actual={actual!r}"
    )
    print(f"PASS: {name} => {actual}")

print("All tests passed.")
