from typing import Dict, List, Tuple

def _collect_block(lines: List[str], start_idx: int) -> Tuple[str, int]:
    """
    Collect a balanced-brace block starting at start_idx (inclusive).
    Returns (block_text, next_index_after_block).
    The first line must contain the opening '{'.
    """
    brace = 0
    buf: List[str] = []
    i = start_idx
    while i < len(lines):
        line = lines[i]
        buf.append(line)
        # Count braces on THIS line
        brace += line.count("{") - line.count("}")
        i += 1
        # Stop exactly when we close the block that began on the first line
        if brace == 0 and "{" in buf[0]:
            break
    return "\n".join(buf), i

def parse_liberty_pin_dirs(lib_path: str) -> Dict[str, Dict[str, str]]:
    """
    Robust Liberty parser to extract pin directions.

    Handles:
      - Single-line pin blocks: pin(A) { direction: input; }
      - Multi-line pin blocks:
            pin(Y) {
              direction: output;
              function: "A'";
            }
    Returns:
      { CELL_NAME_UPPER: { PIN_NAME: 'input'|'output', ... }, ... }
    """
    with open(lib_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    cells: Dict[str, Dict[str, str]] = {}
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        if line.startswith("cell("):
            # Capture entire cell block (including the first 'cell(...) { ... }' line)
            # Ensure the 'cell(' line includes '{'; if not, advance to the next line with '{'
            if "{" not in lines[i]:
                # Move to the line that should contain '{'
                j = i + 1
                while j < n and "{" not in lines[j]:
                    j += 1
                block_text, i = _collect_block(lines, j)
                # Extract cell name from the original 'cell(' line
                header = line
            else:
                block_text, i = _collect_block(lines, i)
                header = lines[i - len(block_text.splitlines())].strip()

            cell_name = header[len("cell("):].split(")")[0].strip().upper()
            cells[cell_name] = {}

            # Now scan inside this cell block for pin blocks.
            # We re-scan the block line-by-line using a brace collector for each pin.
            block_lines = block_text.splitlines()
            k = 0
            while k < len(block_lines):
                pl = block_lines[k].strip()
                if pl.startswith("pin("):
                    # If the 'pin(' line does not contain '{', find the next line that does
                    if "{" not in block_lines[k]:
                        j = k + 1
                        while j < len(block_lines) and "{" not in block_lines[j]:
                            j += 1
                        if j >= len(block_lines):
                            # Malformed pin block; skip
                            k += 1
                            continue
                        pin_block_text, pin_end = _collect_block(block_lines, j)
                        pin_header = pl
                        k = pin_end
                    else:
                        pin_block_text, pin_end = _collect_block(block_lines, k)
                        pin_header = pl
                        k = pin_end

                    # pin header: pin(PINNAME) { ... }
                    pin_name = pin_header[len("pin("):].split(")")[0].strip()

                    # Normalize whitespace in block for robust matching
                    norm = " ".join(pin_block_text.split())
                    # Prefer exact keywords (case-sensitive per Liberty spec)
                    direction = None
                    if "direction: output" in norm:
                        direction = "output"
                    elif "direction: input" in norm:
                        direction = "input"

                    if direction:
                        cells[cell_name][pin_name] = direction
                    continue
                else:
                    k += 1
            # print(f"{cell_name} -> {cells[cell_name]}")
            continue
        else:
            i += 1

    return cells