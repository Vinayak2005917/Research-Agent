from datetime import datetime
import inspect
import os
from dotenv import load_dotenv

load_dotenv()
debug_type = os.getenv("DEBUG_TYPE")
if not debug_type:
    raise RuntimeError("DEBUG_TYPE is not set")

#Empty the file logs.txt
with open("logs.txt", "w") as f:
    f.write("")

def debug_print(contents):
    # Get the caller's frame
    frame = inspect.currentframe().f_back
    
    # Get file name (just the base name, not full path)
    file_name = os.path.basename(frame.f_globals.get("__file__", "unknown"))
    
    # Get function name
    function_name = frame.f_code.co_name
    
    now = datetime.now()
    date_time_info = now.strftime("%H:%M:%S.%f")[:-3]
    if debug_type == "Terminal":
        print(f"\n[{date_time_info}] [{file_name}] [{function_name}] DEBUG: {contents}")
    elif debug_type == "LOCAL":
        with open("logs.txt", "a") as f:
            f.write(f"\n[{date_time_info}] [{file_name}] [{function_name}] DEBUG: {contents}\n")