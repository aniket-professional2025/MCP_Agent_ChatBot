#### Description ####
## The server.py in MCP server acts as the tools that are required to build the MCP agent

# Importing Required Packages
import os
import json
import boto3
from typing import List, Dict
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import streamlit as st

# Environment & Server Setup
load_dotenv()
mcp = FastMCP("LaminateFinder")

# Define the lambda client with region
lambda_client = boto3.client("lambda", region_name=os.getenv("AWS_REGION", "ap-south-1"))
LAMBDA_NAME = "db-connection"

# Calling the Lambda Database
def call_lambda(action: str, params: dict) -> dict:
    """Invoke Lambda and handle nested JSON."""
    try:
        payload = json.dumps({
            "action": action, 
            "params": params
        })

        response = lambda_client.invoke(
            FunctionName = LAMBDA_NAME,
            InvocationType = "RequestResponse",
            Payload=payload.encode("utf-8")
        )

        result = json.load(response.get("Payload"))

        if isinstance(result, dict) and "body" in result:
            try:
                result.update(json.loads(result["body"]))
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse 'body': {e}")
        return result
    except Exception as e:
        print(f"[ERROR] Lambda call failed: {e}")
        return {}

# Fetching all Laminates
def fetch_all_laminates() -> List[dict]:
    """Fetch all laminates."""
    result = call_lambda("getLaminates", {
        "category": None,
        "subcategory": None,
        "page": 1,
        "pageSize": 300,
        "itemType": "Laminates"
    })

    laminates = result.get("laminates", [])
    print(f"[DEBUG] Retrieved {len(laminates)} laminates")
    return laminates

# Fetching Laminats by Id
def fetch_laminate_by_id(laminate_id: str) -> dict:
    """Fetch laminate details by ID."""
    print(f"[DEBUG] Fetching laminate ID: {laminate_id}")
    return call_lambda("getLaminateById", {"id": laminate_id}) or {}

# Fetching Laminates by Prompt
def match_by_prompt(prompt: str, laminates: List[dict]) -> List[dict]:
    prompt = prompt.lower()
    matched = []

    if "blue" in prompt:
        for lam in laminates:
            if any(code.lower().startswith("#1") for code in lam.get("hexcode", [])):
                matched.append(lam)
    elif "dark" in prompt:
        for lam in laminates:
            for code in lam.get("hexcode", []):
                try:
                    if len(code) == 7:
                        r, g, b = int(code[1:3], 16), int(code[3:5], 16), int(code[5:7], 16)
                        if (r + g + b) / 3 < 80:
                            matched.append(lam)
                            break
                except Exception as e:
                    print(f"[WARN] Invalid hex {code} in {lam.get('id')}: {e}")
    else:
        matched = laminates[:10]

    print(f"[DEBUG] Matched {len(matched)} laminates.")
    return matched

# Output Formatting
def format_laminates(laminates: List[dict]) -> List[Dict[str, str]]:
    """Convert raw laminate objects to display-friendly structure."""
    return [
        {
            "name": lam.get("name", ""),
            "sku": lam.get("sku", ""),
            "code": lam.get("code", ""),
            "coverImage": lam.get("coverImage", ""),
            "hexcode": lam.get("hexcode", ""),
            "link": f"https://dummynavigator.centuryply.com/product-details/{lam.get('id')}"
        }
        for lam in laminates
    ]

# Function to Convert a hexcode into RGB format
def hex_to_rgb(hexcode):
    hexcode = hexcode.lstrip("#")
    return tuple(int(hexcode[i:i + 2], 16) for i in (0, 2, 4))

# Function for Measureing distance between two rgb colors
def color_distance(rgb1, rgb2):
    return sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5

# Function to find the laminates in sorted manner
def find_all_laminates_sorted(input_hexcode, laminate_data):
    """Find all laminates sorted by color distance for the given hexcode."""
    input_rgb = hex_to_rgb(input_hexcode)
    ranked = []
    seen_names = set()

    for texture in laminate_data:
        tex_hex_list = texture.get("hexcode", [])
        if not isinstance(tex_hex_list, list) or not tex_hex_list:
            continue

        try:
            distances = [color_distance(input_rgb, hex_to_rgb(h)) for h in tex_hex_list if h.startswith("#")]
            if not distances:
                continue
            min_distance = min(distances)
        except Exception:
            continue

        name = texture.get("name", "")
        if name in seen_names:
            continue

        ranked.append({
            "name": name,
            "sku": texture.get("sku", ""),
            "link": f"https://dummynavigator.centuryply.com/product-details/{texture.get('id')}",
            "distance": min_distance
        })
        seen_names.add(name)

    ranked.sort(key=lambda x: x["distance"])
    return ranked

# Function to process the next batch so that the wait is minimized
def get_next_batch(hexcode, laminate_data, batch_size=4):
    """Get the next batch of laminates for the given hexcode."""
    if "shown_laminates" not in st.session_state:
        st.session_state["shown_laminates"] = {}

    if hexcode not in st.session_state["shown_laminates"]:
        # Initialize for this color
        sorted_laminates = find_all_laminates_sorted(hexcode, laminate_data)
        st.session_state["shown_laminates"][hexcode] = {"index": 0, "sorted": sorted_laminates}

    data = st.session_state["shown_laminates"][hexcode]
    start = data["index"]
    end = start + batch_size
    data["index"] = end
    return data["sorted"][start:end]

# Defining the MCP tools
@mcp.tool()
def find_laminates(prompt: str) -> List[dict]:
    """Find laminates based on user prompt."""
    print(f"[TOOL] find_laminates called with prompt: {prompt}")
    laminates = fetch_all_laminates()
    matched = match_by_prompt(prompt, laminates)
    print(f"[DEBUG] Tool returning {len(matched)} laminates")
    return format_laminates(matched)

# Defining MCP Resources
@mcp.resource("laminates://{laminate_id}")
def get_laminate_by_id(laminate_id: str) -> dict:
    """Get laminate details by ID."""
    print(f"[RESOURCE] get_laminate_by_id called with ID: {laminate_id}")
    laminate = fetch_laminate_by_id(laminate_id)
    return laminate if laminate else {"error": "Laminate not found"}

# Run the MCP Client
if __name__ == "__main__":
    mcp.run(transport = 'stdio')
    # # For local debug only
    # print('-----------------------------------------------------')
    # print("[TEST] Testing `find_laminates()` tool...")
    # results = find_laminates("Find some blue laminates")
    # print(json.dumps(results, indent=2))
    # print("-----------------------------------------------------")
