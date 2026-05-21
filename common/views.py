from decimal import Decimal

# Create your views here.
def _integer_to_words(number: int) -> str:
    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
        "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
        "Sixteen", "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy",
        "Eighty", "Ninety",
    ]

    if number == 0:
        return "Zero"
    if number < 20:
        return ones[number]
    if number < 100:
        return tens[number // 10] + (" " + ones[number % 10] if number % 10 else "")
    if number < 1000:
        return (
            ones[number // 100]
            + " Hundred"
            + (" " + _integer_to_words(number % 100) if number % 100 else "")
        )
    if number < 100000:
        return (
            _integer_to_words(number // 1000)
            + " Thousand"
            + (" " + _integer_to_words(number % 1000) if number % 1000 else "")
        )
    if number < 10000000:
        return (
            _integer_to_words(number // 100000)
            + " Lakh"
            + (" " + _integer_to_words(number % 100000) if number % 100000 else "")
        )
    return (
        _integer_to_words(number // 10000000)
        + " Crore"
        + (" " + _integer_to_words(number % 10000000) if number % 10000000 else "")
    )


def amount_to_indian_words(amount: Decimal) -> str:
    amount = Decimal(amount or 0).quantize(Decimal("0.01"))
    rupees = int(amount)
    paise = int((amount - Decimal(rupees)) * 100)

    words = _integer_to_words(rupees) + " Rupees"
    if paise:
        words += " and " + _integer_to_words(paise) + " Paise"
    return words + " Only"
