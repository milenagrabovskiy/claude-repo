"""Who owes what, after a group of people have paid for things.

Amounts are integer cents throughout. Floats are not used anywhere in this
module, because binary floating point cannot represent 0.10 exactly and money
arithmetic that drifts by a fraction of a cent per operation is the classic
way a ledger stops balancing.
"""


def split_evenly(amount_cents, participants):
    """Divide one expense between the people who shared it.

    Returns {person: cents_they_owe}.
    """
    share = amount_cents // len(participants)
    return {person: share for person in participants}


def balances(expenses, people):
    """Net position per person, in cents. Positive means they are owed money.

    Every expense moves money twice: the payer is credited the full amount, and
    each participant is debited their share. Across a complete set of expenses
    those two movements should cancel exactly, so the net positions sum to zero.

    If they don't sum to zero, money has been invented or destroyed somewhere
    upstream -- which is not something this function can correct on its own
    without hiding the cause.
    """
    net = {person: 0 for person in people}
    for expense in expenses:
        net[expense["paid_by"]] += expense["amount_cents"]
        shares = split_evenly(expense["amount_cents"], expense["participants"])
        for person, share in shares.items():
            net[person] -= share
    return net


def validate_expense(data):
    """Check a submitted expense before it reaches the ledger.

    Returns a list of error messages; an empty list means the expense is valid.
    Rejecting bad input here matters more than usual, because a malformed
    expense doesn't fail loudly -- it quietly breaks the zero-sum invariant
    for every balance computed afterwards.
    """
    if not isinstance(data, dict):
        return ["body must be a JSON object"]

    errors = []

    amount = data.get("amount_cents")
    # bool is a subclass of int, so True would otherwise pass as 1 cent.
    if not isinstance(amount, int) or isinstance(amount, bool):
        errors.append("amount_cents must be an integer number of cents")
    elif amount <= 0:
        errors.append("amount_cents must be positive")

    paid_by = data.get("paid_by")
    if not isinstance(paid_by, str) or not paid_by.strip():
        errors.append("paid_by must be a non-empty string")

    participants = data.get("participants")
    if not isinstance(participants, list) or not participants:
        errors.append("participants must be a non-empty list")
    elif not all(isinstance(p, str) and p.strip() for p in participants):
        errors.append("each participant must be a non-empty string")
    elif len(set(participants)) != len(participants):
        # split_evenly divides by len(participants) but keys a dict by name, so
        # a duplicate is debited once while still shrinking everyone's share.
        errors.append("participants must not contain duplicates")

    return errors
