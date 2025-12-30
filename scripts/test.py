"""
Script de utilidad para ejecutar tests localmente con configuración adecuada.
"""
import subprocess
import sys


def run_tests():
    """Ejecuta la suite de tests."""
    print("Ejecutando tests...")

    cmd = [
        "pytest",
        "-v",
        "--cov=api",
        "--cov-report=html",
        "--cov-report=term-missing"
    ]

    result = subprocess.run(cmd)
    return result.returncode


def run_lint():
    """Ejecuta linters."""
    print("Ejecutando linters...")

    # Black
    print("\n Black (formato)...")
    subprocess.run(["black", "api/", "tests/"])

    # Flake8
    print("\n Flake8 (linting)...")
    result = subprocess.run(["flake8", "api/", "tests/"])

    return result.returncode


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "test":
            sys.exit(run_tests())
        elif command == "lint":
            sys.exit(run_lint())
        elif command == "all":
            lint_result = run_lint()
            if lint_result != 0:
                print("  Linting falló")
                sys.exit(lint_result)

            test_result = run_tests()
            if test_result != 0:
                print("  Tests fallaron")
                sys.exit(test_result)

            print(" Todo OK!")
            sys.exit(0)
        else:
            print(f"Comando desconocido: {command}")
            print("Uso: python scripts/test.py [test|lint|all]")
            sys.exit(1)
    else:
        print("Uso: python scripts/test.py [test|lint|all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
