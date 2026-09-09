import re
import shlex


# System default
DEFAULT_TIME_LIMIT = 3.0
DEFAULT_MEMORY_LIMIT = 128


languages = {
    "python": {
        "file_ext": ".py",
        "compile_cmd": None,
        "run_cmd": "python3 {src}",
        "time_limit": 3.0,
        "memory_limit": 128
    },

    "cpp": {
        "file_ext": ".cpp",
        "compile_cmd": "g++ {src} -o {exe} -std=c++14",
        "run_cmd": "{exe}",
        "time_limit": 3.0,
        "memory_limit": 128
    },
    # languages["cpp"]["compile_cmd"]
    # g++ {src} -o {exe} -std=c++14

    "c": {
        "file_ext": ".c",
        "compile_cmd": "gcc {src} -o {exe}",
        "run_cmd": "{exe}",
        "time_limit": 3.0,
        "memory_limit": 128
    }
}

# `file_ext` is the extension of the source file: .cpp
# so when the user sends:
#     #include <iostream>
#     int main() {
#         ...
#     }
# Judge will create a file: source.cpp

# `compile_cmd` is the compile command
#     "g++ {src} -o {exe} -std=c++14"
# {src} is a placeholder for the source file
# {exe} is a placeholder of the executable to be built.
# We will use this later:
#     compile_cmd.format(
#         src=source_path,
#         exe=executable_path
#     )
# example:
#     source_path = "/tmp/abc/source.cpp"
#     executable_path = "/tmp/abc/program"
# g++ {src} -o {exe} -std=c++14 -> g++ /tmp/abc/source.cpp -o /tmp/abc/program -std=c++14



def validate_language_config(language): # This function is called when a new language is added to the system.
    # Check language name
    if not re.fullmatch(
        r"[A-Za-z0-9_+\-]{1,32}", # A to Z, a to z, 0 to 9,_ , +, -, 1 to 32 letters
                                  # example: c++, python3, java-21, c-sharp
        language.name
    ):
        return False, "invalid language name"

    # Extension must look like .cpp, .py, .c ...
    if (
        not language.file_ext.startswith(".")
        or "/" in language.file_ext
        or "\\" in language.file_ext
    ):
        return False, "invalid file extension"

    # Limits
    if (
        language.time_limit is not None
        and language.time_limit <= 0
    ):
        return False, "time_limit must be greater than 0"

    if (
        language.memory_limit is not None
        and language.memory_limit <= 0
    ):
        return False, "memory_limit must be greater than 0"

    commands = [
        language.compile_cmd,
        language.run_cmd
    ]

    # Do not allow shell control characters.
    # Commands are executed without shell=True.
    # we dont want `;` in g++ {src} -o {exe}; rm -rf something, or command1 && command2
    # because this might cause the shell to perceive it as a different command.
    dangerous = [";", "&&", "||", ">", "<", "`"]

    for command in commands:
        if command is None:
            continue # Python without a compile command is not a problem.

        for token in dangerous:
            if token in command:
                return False, "unsafe command"

        try:
            parts = shlex.split(command) # Take the command string and separate it into a list of its individual parts.
            # command = "g++ {src} -o {exe} -std=c++14" --> parts = shlex.split(command) --> 
                # [
                #     "g++",
                #     "{src}",
                #     "-o",
                #     "{exe}",
                #     "-std=c++14"
                # ]
            # example: command = 'python3 "my program.py"'
            # command.split() --> ["python3", '"my', 'program.py"']
            # shlex.split(command) --> ["python3", "my program.py"]
        except ValueError:
            return False, "invalid command"

        if len(parts) == 0:
            return False, "empty command"

    # Compile command must know source file
    if (
        language.compile_cmd is not None
        and "{src}" not in language.compile_cmd
    ):
        return False, "compile_cmd must contain {src}"

    # Run command needs source or executable
    if (
        "{src}" not in language.run_cmd
        and "{exe}" not in language.run_cmd
    ):
        return False, "run_cmd must contain {src} or {exe}"

    return True, ""

