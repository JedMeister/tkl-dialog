# Copyright (c) 2022 TurnKey GNU/Linux <admin@turnkeylinux.org>


def fatal(e: str):
    print("error:", e, file=sys.stderr)
    sys.exit(1)


def usage(e: str = None, doc: str = None):
    if e:
        print("Error:", e, file=sys.stderr)

    print(f"Syntax: {sys.argv[0]}", file=sys.stderr)
    print(doc.strip(), file=sys.stderr)
    sys.exit(1)


def password_complexity(password: str) -> int:
    """return password complexity score from 0 (invalid) to 4 (strong)"""

    lowercase = re.search('[a-z]', password) is not None
    uppercase = re.search('[A-Z]', password) is not None
    number = re.search(r'\d', password) is not None
    nonalpha = re.search(r'\W', password) is not None

    return sum([lowercase, uppercase, number, nonalpha])
