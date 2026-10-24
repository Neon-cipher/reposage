"""Unit tests for AST and static code analyzers."""
from reposage.analyzers.python_ast import analyze_python_file
from reposage.analyzers.generic import analyze_generic_file, extract_package_dependencies


def test_python_ast_entrypoint_and_symbols():
    code = """
class Calculator:
    def add(self, a, b):
        # TODO: support floating point precision
        return a + b

def standalone_helper():
    pass

if __name__ == '__main__':
    calc = Calculator()
    print(calc.add(1, 2))
"""
    entrypoints, symbols, todos = analyze_python_file("calc.py", code)

    assert len(entrypoints) == 1
    assert entrypoints[0].start_line > 0
    assert "class Calculator" in symbols[0]
    assert any("def add()" in s for s in symbols)
    assert any("def standalone_helper()" in s for s in symbols)
    
    assert len(todos) == 1
    assert todos[0].tag == "TODO"
    assert "support floating point" in todos[0].text
    assert todos[0].line_number == 4


def test_generic_analyzer_js():
    code = """
export function processUser(id) {
    // FIXME: handle null id error
    return { id: id };
}

app.listen(3000, () => {
    console.log("Server running");
});
"""
    entrypoints, symbols, todos = analyze_generic_file("server.js", code)

    assert len(symbols) >= 1
    assert "function processUser()" in symbols[0]
    assert len(entrypoints) == 1
    assert entrypoints[0].start_line == 7
    assert len(todos) == 1
    assert todos[0].tag == "FIXME"


def test_extract_dependencies_json():
    pkg_json = """{
        "name": "sample",
        "dependencies": {
            "express": "^4.18.2"
        },
        "devDependencies": {
            "jest": "^29.0.0"
        }
    }"""
    deps = extract_package_dependencies("package.json", pkg_json)
    assert "express@^4.18.2" in deps
    assert "jest@^29.0.0" in deps
