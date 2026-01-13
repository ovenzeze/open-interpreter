from interpreter.core.utils.truncate_output import truncate_output

def test_truncate_short():
    data = "Short string"
    assert truncate_output(data, 100) == data

def test_truncate_long_no_error():
    data = "A" * 200
    # max_output_chars=100
    truncated = truncate_output(data, 100)
    assert "..." in truncated
    assert "Output truncated" in truncated
    assert truncated != data

def test_truncate_long_with_error():
    # Make data huge so truncation is obvious, and include newlines so line-expansion doesn't eat the whole string
    lines = ["Line " + str(i) for i in range(1000)]
    data = "\n".join(lines)
    # data length is roughly 1000 * 8 = 8000 chars.

    # Insert an error in the middle
    data += "\nError: Something bad happened\n"
    data += "\n".join(["More " + str(i) for i in range(1000)])

    truncated = truncate_output(data, 1000)

    assert "Error" in truncated
    assert "Output truncated" in truncated
    assert len(truncated) < len(data)

def test_truncate_empty():
    assert truncate_output("", 100) == ""

def test_truncate_exact_length():
    data = "A" * 100
    assert truncate_output(data, 100) == data
