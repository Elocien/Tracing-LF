#!/usr/bin/env python3

# Copyright (C) 2020 TU Dresden
# All rights reserved.
#
# Authors:
#   Christian Menard


import argparse
import bt2
import json
import os
import sys


pid_registry = {}
tid_registry = {}


def get_ids(process, thread):
    if process not in pid_registry:
        pid_registry[process] = len(pid_registry) + 1
        tid_registry[process] = {}
    pid = pid_registry[process]
    tid_reg = tid_registry[process]
    if thread not in tid_reg:
        tid_reg[thread] = len(tid_reg)
    tid = tid_reg[thread]
    return pid, tid


def main():
    parser = argparse.ArgumentParser(
        description="Convert a CTF trace to a json trace viewable with google "
                    "chrome")
    parser.add_argument("ctf", metavar="CTF", type=str,
                        help="Path to the CTF trace")
    parser.add_argument("-o", "--output", metavar="OUT", type=str,
                        default="trace.json", help="the output file")
    args = parser.parse_args()

    if not os.path.isdir(args.ctf):
        raise NotADirectoryError(args.ctf)

    ctf_path = None
    for root, dirs, files in os.walk(args.ctf):
        for f in files:
            if f == "metadata":
                if ctf_path is None:
                    ctf_path = str(root)
                else:
                    raise RuntimeError("%s is not a single trace (contains "
                                       "more than one metadata file!" %
                                       args.ctf)

    if ctf_path is None:
        raise RuntimeError("%s is not a CTF trace (does not contain a metadata"
                           " file)" % args.ctf)

    # Find the `ctf` plugin (shipped with Babeltrace 2).
    ctf_plugin = bt2.find_plugin('ctf')

    # Get the `source.ctf.fs` component class from the plugin.
    fs_cc = ctf_plugin.source_component_classes['fs']

    # Create a trace collection message iterator, instantiating a single
    # `source.ctf.fs` component class with the `inputs` initialization
    # parameter set to open a single CTF trace.
    msg_it = bt2.TraceCollectionMessageIterator(bt2.ComponentSpec(fs_cc, {
        # Get the CTF trace path from the first command-line argument.
        'inputs': [ctf_path],
    }))

    # keep a list of events to dump later to JSON
    trace_events = []
    
    execution_messages_dict = {}

    # Iterate the trace messages.
    for msg in msg_it:
        # `bt2._EventMessageConst` is the Python type of an event message.
        if type(msg) is bt2._EventMessageConst:
            event = msg.event
            

            if (event.name == "reactor_cpp:reaction_execution_starts"):
                execution_messages_dict[str(event["reaction_name"])] = msg
                
            elif (event.name == "reactor_cpp:reaction_execution_finishes"):
                
                value = execution_messages_dict[str(event["reaction_name"])]
                
                trace_events.append(reaction_execution_starts_to_dict(value))
                trace_events.append(reaction_execution_finishes_to_dict(msg))
            elif (event.name == "reactor_cpp:schedule_action"):
                trace_events.append(schedule_action_to_dict(msg))
            elif (event.name == "reactor_cpp:trigger_reaction"):
                trace_events.append(trigger_reaction_to_dict(msg))
  

    data = {
        "traceEvents": trace_events,
    }
    with open(args.output, 'w') as outfile:
        json.dump(data, outfile, indent=2)




def get_timestamp_us(msg):
    timestamp_ns = msg.default_clock_snapshot.ns_from_origin
    return timestamp_ns / 1000.0


def reaction_execution_starts_to_dict(msg):
    event = msg.event
    return {
        "name": str(event["reaction_name"]),
        "cat": "Execution",
        "ph": "B",
        "ts": get_timestamp_us(msg),
        "reactor": "Execution",
        "reaction": "worker " + str(event["worker_id"]),
    }


def reaction_execution_finishes_to_dict(msg):
    event = msg.event
    return {
        "name": str(event["reaction_name"]),
        "cat": "Execution",
        "ph": "E",
        "ts": get_timestamp_us(msg),
        "reactor": "Execution",
        "reaction": "worker " + str(event["worker_id"]),
    }


def schedule_action_to_dict(msg):
    event = msg.event
    return {
        "name": "schedule",
        "cat": "Reactors",
        "ph": "i",
        "ts": float(event["timestamp_ns"]) / 1000.0,
        "reactor": str(event["reactor_name"]),
        "reaction": str(event["action_name"]),
        "s": "t",
        "cname": "terrible",
        "args": {
            "microstep": int(event["timestamp_microstep"])
        }
    }


def trigger_reaction_to_dict(msg):
    event = msg.event
    return {
        "name": "trigger",
        "cat": "Reactors",
        "ph": "i",
        "ts": float(event["timestamp_ns"]) / 1000.0,
        "reactor": str(event["reactor_name"]),
        "reaction": str(event["reaction_name"]),
        "s": "t",
        "cname": "light_memory_dump",
        "args": {
            "microstep": int(event["timestamp_microstep"])
        }
    }


if(__name__ == "__main__"):
    main()
