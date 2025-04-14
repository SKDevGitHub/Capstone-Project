def format_data(data):
    """Formats the given data dictionary into a readable string."""
    formatted_output = "-" * 40 + "\n"
    formatted_output += "Received Data:\n"

    for key, value in data.items():
        formatted_output += f"  {key}: {value}\n"

    formatted_output += "-" * 40
    return formatted_output

# Example usage (assuming 'data' is your dictionary)
data = {'signature': '25EYY2KccEzcqMUt8yfZMeEdcwcL7ytq3zeCyZvTRsngNm7Chy15BR2YU8ENFwgCumayApUsXKNpBiTjMxE7cvSw', 'mint': 'BqmTtcVb3U82npDGRHb4tsej5S68ne7VxqCz13mEteQ4', 'traderPublicKey': '9ZCrb9iKawp1e5Gw3r2BpHpCZQbHFg6DLguzQ5SkP2Eg', 'txType': 'create', 'initialBuy': 153285714.285713, 'solAmount': 5, 'bondingCurveKey': 'w1zoUqqCV8kdTq7C8EesnC9jD6YfWBtoePdtTMdaokq', 'vTokensInBondingCurve': 919714285.714287, 'vSolInBondingCurve': 34.99999999999995, 'marketCapSol': 38.05529667598623, 'name': 'Super Mario World', 'symbol': 'SMW', 'uri': 'https://ipfs.io/ipfs/Qmat8VGrszvbHU1yXQFhUYtKreLpbFwdkHcx6jbDiXXMw9', 'pool': 'pump'}

print(format_data(data))

# or if you want to use it within your websocket script.
import asyncio
import websockets
import json
from datetime import datetime

async def subscribe_new_tokens():
    """Subscribes to token creation events from pumpportal.fun and formats the output."""
    uri = "wss://pumpportal.fun/api/data"
    try:
        async with websockets.connect(uri) as websocket:
            payload = {
                "method": "subscribeNewToken",
            }
            await websocket.send(json.dumps(payload))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    if "method" in data and data["method"] == "newToken":
                        token_data = data["data"]
                        mint = token_data.get("mint", "N/A")
                        creator = token_data.get("creator", "N/A")
                        timestamp_unix = token_data.get("timestamp", 0)
                        try:
                            timestamp_dt = datetime.fromtimestamp(timestamp_unix / 1000.0) #divide by 1000 to convert from milliseconds to seconds.
                            timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            timestamp_str = "N/A"

                        print("-" * 40)
                        print(f"New Token Created:")
                        print(f"  Mint: {mint}")
                        print(f"  Creator: {creator}")
                        print(f"  Timestamp: {timestamp_str}")
                        print("-" * 40)

                    elif "method" in data:
                        print(f"Received other method: {data['method']}")

                    else:
                        print(format_data(data)) #format the data here.

                except json.JSONDecodeError:
                    print(f"Error decoding JSON: {message}")
                except KeyError as e:
                    print(f"KeyError: {e} in data: {data}")
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")

    except websockets.exceptions.ConnectionClosedError:
        print("Connection closed unexpectedly.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(subscribe_new_tokens())