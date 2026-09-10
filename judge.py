import asyncio
import json
import os
import shlex
import signal
import tempfile
import time

from language_manager import languages, DEFAULT_TIME_LIMIT, DEFAULT_MEMORY_LIMIT

from submission_store import submissions


def normalize_output(output: str):
    """
    Ignore:
    1. trailing spaces on each line
    2. extra newlines at the end
    """

    lines = output.splitlines() # seperate strings line by line
    # Example: ["10    ", "20", ""]

    lines = [ line.rstrip() for line in lines ] # remove whitespace on the right
    # ["10", "20", ""]
    
    while lines and lines[-1] == "": # If the last line is blank, keep deleting it
        lines.pop()
    # ["10", "20"]

    return "\n".join(lines) # reassamble it back to the initial input


def get_memory_usage_mb(pid: int): # input `pid` or Process ID
    """
    Read current RSS memory usage from Linux /proc.
    Return memory usage in MB.
    """

    status_path = f"/proc/{pid}/status" # 1

    try:
        with open( # 2
            status_path,
            "r",
            encoding="utf-8"
        ) as f:

            for line in f: # 3
                if line.startswith("VmRSS:"): # 4
                    parts = line.split() # 5

                    # VmRSS is in kB
                    memory_kb = int(parts[1]) # 6

                    return memory_kb / 1024 # 7
# 1. If we open a C++ program, Linux ight assign the process ID = 15372, at /proc/15372/status
#    So we create a path: `status_path = f"/proc/{pid}/status"`
# 2. open File
# 3., 4. might encounter `VmRSS: 20480 kB`
# 5. split: ["VmRSS", "20480", "kB"]
# 6. memory_kb = 20480
# 7. convert into MB, OJ wants MB and 1024 kB = 1 MB

    # try and except
    # `Try` reading the memory information.
    # If any of these three types of errors occur, don't let the program crash, skip them
    except (FileNotFoundError, ProcessLookupError, ValueError):
        pass

    return 0


async def monitor_memory(process, memory_limit): # continuously monitoring the RAM
    # Example: memory_limit = 128 MB
    """
    Monitor process memory.
    Kill it when memory usage exceeds the limit.

    Return True if MLE happened.
    """

    while process.returncode is None: # As long as the process is not complete, continue to monitor it

        memory = get_memory_usage_mb(process.pid) # check memory

        if memory > memory_limit:
            # If the memory usage exceeds the memory limit, 
            # kill this process and return true, which means 
            # yes, this program has exceeded the memory limit.
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                # os. A Python module for handling operating system tasks. -> import above
                # signal. A module for managing signals in the operating system. -> import above
            except (ProcessLookupError, PermissionError):
                try: # If killpg() doesn't work, then try process.kill() instead.
                     # However, process.kill() itself might throw an error, so it needs its own try-except.
                    process.kill()
                except ProcessLookupError:
                    pass
            # nested try-except
            # Try method A first. If A doesn't work, try method B. 
            # And if B doesn't work either, just let it go.
            return True

        await asyncio.sleep(0.01) # If not TLE, wait 0.01s and check again

    return False


async def kill_process(process):
    """
    Kill the submitted program and its process group.
    """

# Example: 
#     while (true) {
#     }
    
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)

    except (ProcessLookupError, PermissionError):
        try:
            process.kill()
        except ProcessLookupError:
            pass

    try: # Wait until the child process finishes and acknowledges its completion (returncode).
        await process.wait()
    except ProcessLookupError:
        pass


async def run_testcase(run_command, testcase_input, expected_output, time_limit, memory_limit):
    """
    Run one testcase.
    Possible results: AC, WA, TLE, MLE, RE, UNK
    """
    # This is a function that runs the user's program with a set of test cases.
    
    try:
        command = shlex.split(run_command) # "python3 /tmp/source.py" -> ["python3", "/tmp/source.py"]

        process = await asyncio.create_subprocess_exec( # Open the `user` progeam
            # Open another program process.
            # Similar to `python3 source.py` in Python or `./program` in cpp
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # We connected the pipe in three ways:
            # `stdin` = Sends a test case to the program.
            # `stdout` = receives what the user `print` /`cout`
            # `stderr` = receive error
            start_new_session=True
        )

        memory_task = asyncio.create_task( # monitor_memory() runs concurrently with the user program.
            # run user program ──────────────────→
            # monitor RAM      check check check →
            # -> asyncio
            monitor_memory(process, memory_limit)
        )

        start_time = time.perf_counter()

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(
                    input=testcase_input.encode()
                ),
                timeout=time_limit
            )

        except asyncio.TimeoutError:

            await kill_process(process)

            if not memory_task.done():
                memory_task.cancel()

            return {
                "result": "TLE",
                "stdout": "",
                "stderr": ""
            }

        elapsed = time.perf_counter() - start_time

        # Check whether memory monitor killed the process
        memory_exceeded = False

        if memory_task.done():
            try:
                memory_exceeded = memory_task.result()
            except asyncio.CancelledError:
                pass

        else:
            memory_task.cancel()
            try:
                await memory_task
            except asyncio.CancelledError:
                pass

        stdout = stdout.decode(errors="replace")

        stderr = stderr.decode(errors="replace")

        if memory_exceeded:
            return {
                "result": "MLE",
                "stdout": stdout,
                "stderr": stderr
            }

        if process.returncode != 0: # if normal returncode 0, else != 0
            return {
                "result": "RE",
                "stdout": stdout,
                "stderr": stderr
            }

        if (normalize_output(stdout) == normalize_output(expected_output)):
            result = "AC"
        else:
            result = "WA"

        return {
            "result": result,
            "stdout": stdout,
            "stderr": stderr,
            "time": elapsed
        }

    except Exception as e:
        return {
            "result": "UNK",
            "stdout": "",
            "stderr": str(e)
        }
    #          run
    #           │
    #    ┌──────┴──────┐
    #  timeout?       no
    #    │              │
    #   TLE        memory exceeded?
    #                   │
    #              yes ─┴─ no
    #               │       │
    #              MLE    crashed?
    #                      │
    #                 yes ─┴─ no
    #                  │       │
    #                 RE    compare
    #                         │
    #                     ┌───┴───┐
    #                    same    different
    #                     │         │
    #                    AC        WA


async def compile_source(compile_command, temp_dir):
    """
    Compile languages such as C/C++.
    Return: success CE UNK
    """

    try:
        process = await asyncio.create_subprocess_exec( # G++ process
            *shlex.split(compile_command),

            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,

            start_new_session=True
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=15 # no more than 15 sec
            )

        except asyncio.TimeoutError: # cannot compile
            await kill_process(process)
            return {    
                "result": "CE",
                "message": "compilation timeout"
            }

        stdout = stdout.decode(errors="replace")

        stderr = stderr.decode(errors="replace")

        # Do not expose temporary server path
        stdout = stdout.replace(temp_dir,"<temp>")

        stderr = stderr.replace(
            temp_dir, "<temp>"
        )

        if process.returncode != 0:

            return {
                "result": "CE",
                "message": stderr
            }

        return {
            "result": "success",
            "message": stderr
        }

    except Exception:

        return {
            "result": "UNK",
            "message": "compiler execution failed"
        }


def calculate_limits(problem, language):
    # In summary, how many seconds are allowed for this submission and how much RAM is required?
    """
    Priority:
    problem
        ↓
    language
        ↓
    system default
    """

    time_limit = problem.get("time_limit")

    if time_limit is None:
        time_limit = language.get("time_limit")

    if time_limit is None:
        time_limit = DEFAULT_TIME_LIMIT

    memory_limit = problem.get("memory_limit")

    if memory_limit is None:
        memory_limit = language.get("memory_limit")

    if memory_limit is None:
        memory_limit = DEFAULT_MEMORY_LIMIT

    return (float(time_limit), int(memory_limit))


async def judge_submission(
    submission_id,
    submission
):
    """
    Judge one submission asynchronously.
    """

    try:

        problem_path = os.path.join("problems",f"{submission.problem_id}.json") # Find the problem file.

        # Read problem
        with open( problem_path, "r", encoding="utf-8" ) as f:
            problem = json.load(f) # Read the problem and convert it into a dictionary.

        language = languages[submission.language]

        time_limit, memory_limit = (
            calculate_limits( problem, language )
        )
        # Example: submission.language == "cpp" as same as language = languages["cpp"]
        # config:
            # {
            #     "file_ext": ".cpp",
            #     "compile_cmd": "g++ {src} -o {exe}",
            #     "run_cmd": "{exe}",
            #     ...
            # }

        testcases = problem["testcases"]

        counts = len(testcases) * 10
        # 1 testcase = 10 points
        # 3 testcases * 10 = 30 points

        # Create a temporary room for this submission
        # ex: /tmp/tmpabc123/
        # then create source path and executable path
        with tempfile.TemporaryDirectory() as temp_dir: 

            # Use absolute paths
            source_path = os.path.abspath(
                os.path.join(
                    temp_dir,
                    "source" + language["file_ext"]
                )
            )
            # Example: /tmp/tmpabc123/source.cpp

            executable_path = os.path.abspath(
                os.path.join(
                    temp_dir,
                    "program"
                )
            )
            # Example: /tmp/tmpabc123/program

            # Save submitted code
            with open(source_path, "w", encoding="utf-8") as f:

                f.write(submission.code) # So, if the original code was a string in JSON, now it's become a real file.

            # ---------------------
            # Compile
            # ---------------------

            compile_info = None
            compile_cmd = language.get("compile_cmd")

            if compile_cmd: # If C++: "g++ {src} -o {exe}"

                compile_command = compile_cmd.format( # g++ {src} -o {exe}    ->    g++ /tmp/.../source.cpp -o /tmp/.../program
                    src=source_path, exe=executable_path
                )

                compile_info = await compile_source(
                    compile_command, temp_dir # If the compiler breaks, return 0
                    # Stop judging because if it doesn't compile, there's no executable to run the test cases.
                )

                if compile_info["result"] != "success":
                    submissions[submission_id].update({
                        "status": "success",
                        "score": 0,
                        "counts": counts,
                        "compile_info": compile_info,
                        "run_info": None,
                        "error_info": ""
                    })

                    return

            # ---------------------
            # Run
            # ---------------------

            run_command = language["run_cmd"].format(
                src=source_path,
                exe=executable_path
            )

            score = 0
            results = []

            for testcase in testcases: # loop every testcase
                result = await run_testcase(
                    run_command,
                    testcase["input"],
                    testcase["output"],
                    time_limit,
                    memory_limit
                )

                results.append(
                    result["result"]
                )

                if result["result"] == "AC":
                    score += 10
                # Example: results = ["AC", "WA", "AC"]

            # Find final judging result
            final_result = "AC"
            priority = ["UNK", "MLE", "TLE", "RE", "WA"] # example: TLE <<< WA

            for status in priority:

                if status in results:
                    final_result = status
                    break

            submissions[submission_id].update({
                "status": "success",
                "score": score,
                "counts": counts,
                "compile_info": compile_info,
                "run_info": {
                    "result": final_result,
                    "message":
                        f"{len(testcases)} test cases finished"
                },
                "error_info": ""
            })
            # Example:
            # submissions["abc123"] = {
            #     "status": "success",
            #     "score": 20,
            #     "counts": 30,
            #     ...
            # }
            # When the webpage makes a GET request to /api/submissions/abc123, 
            # main.py reads the data from submissions and sends the results back to the user.

    except Exception:

        # Do not expose server internal paths/errors
        submissions[submission_id].update({
            "status": "error",
            "score": None,
            "counts": None,
            "compile_info": None,
            "run_info": None,
            "error_info": "judging task failed"
        })