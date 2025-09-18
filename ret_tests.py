import multiprocessing
import sys
sys.path.append('/mnt/bigdata/multiplier')
import process_mx
import engine
#import matplotlib.pyplot as plt
import extractRetvals as extract
import os
import collections

def writeToCsv(line, fileName):
    with open(fileName, 'a') as f: 
        f.write(line + '\n')


def test_library(index, headers):
    idx = process_mx.Index_Target_Header(index, headers, False)
    function_list, macros, enums, fps, aliases = idx.extractArtifacts()
    compatibility = engine.CheckCompatibility(idx.index, aliases, enums, "", False, False)
    functions = engine.APIfunctions()
    compatibility.process_functions(functions, function_list, "")

    funcs = functions.getAllFunctions()
    extracted = extract.ExtractLib(idx.index)
    separator = "\n"
 
    for fun in extracted: 
        writeToCsv(separator.join(str(item) for item in extracted[fun].retlist ), "outputData.csv")
    #somethingElse = functions.?
    #for function in funcs:
        #print(function)
    #compatibility.checkrets(funcs)
    #extracted = extract.ExtractLib(index)
    #plot_retval_stats(collect_retvals(funcs))
   # global tests_total
   # global fail_total

    #fail_count = 0
    #for name, expected, retval in name_and_expected:
       # target = next((f for f in funcs if f.name == name), None)

       # if target.ret_status_check == expected:
         #   print(f"{name} passed")
      #  else:
        #    print(f"{name} FAILED")
        #    print("Expected:")
        #    print(f"  {expected}")
         #   print("Actual:")
        #    print(f"  {target.ret_status_check}")
         #   fail_count += 1
         #   print("\n")
    #print(f"{index}: {(len(name_and_expected)-fail_count)/len(name_and_expected) * 100}% passed.")

def collect_retvals(tasks):
   
   manager = multiprocessing.Manager()
   retvals = manager.dict()

   def worker(index_path, wanted, out_dict):
        extracted = extract.ExtractLib(index_path)  # {name: Function}
        for name, idx in wanted.items():
            fn = extracted.get(name)
    
            if fn and idx < len(fn.retlist):
               out_dict[name] = fn.retlist[idx].to_dict()
            else: 
               print(f"Warning: Retval out of range in {name}. Expected {idx}, but has {len(fn.retlist)}")
               out_dict[name] = None

   procs = []
   for index_path, _headers, name_expected in tasks:
       #print(f"{index_path} - {name_expected[0][0]}")
       wanted = {name: idx for name, _exp, idx in name_expected}
       p = multiprocessing.Process(target=worker,
                                    args=(index_path, wanted, retvals))
       p.start()
       procs.append(p)

   for p in procs:
       p.join()

   return dict(retvals)

def plot_retval_stats(retvals: dict[str, dict], outdir="plots"):
    import os
    os.makedirs(outdir, exist_ok=True)

    stats = {
        "depth": [],
        "in_loop": [],
        "in_conditional": [],
        "is_var": [],
        "is_callexpr": [],
        "is_enum": [],
        "error_func_called": [],
        "callexprs_in_block": [],
        "is_last": [],
    }

    for rv in retvals.values():
        if not rv:
            continue
        for key in stats:
            value = rv.get(key)
            if value is not None:
                stats[key].append(value)

    for key, values in stats.items():
        if not values:
            continue
 #   print ("Key", key, "Value", values)

       # plt.figure()
        #if isinstance(values[0], bool):
       #     counter = collections.Counter(values)
       #     plt.bar([str(k) for k in counter.keys()], counter.values())
     #   else:
       #     bins = range(min(values), max(values) + 2)
        #    plt.hist(values, bins=bins, align='left', rwidth=0.8, edgecolor='black')
            
      #  plt.title(f"{key} distribution")
      #  plt.xlabel(key)
      #  plt.ylabel("Frequency")
       # plt.tight_layout()
        #outfile = os.path.join(outdir, f"{key}_distribution.png")
        #plt.savefig(outfile)
        #plt.close()

def run_test(args):
    try:
        test_library(*args)
    except Exception as e:
        print(e)

tasks = [
    ("../demos/lexbor/lib.db", ["document.h", "parser.h", "unicode.h"]),
    ("../demos/sqlite/lib.db", ["sqlite3.h"]),
    """


    ("../demos/hdf5/lib.db", ["hdf5.h", "H5Fpublic.h"]),

    ("../demos/stormlib/lib.db", ["StormLib.h"]),

    ("../demos/openexr/lib.db", ["ImfCRgbaFile.h"]),

    ("../demos/magic/lib.db", ["magic.h"]),

   
    ("../demos/fyaml/lib.db", ["libfyaml.h"]),

    ("../demos/ical/lib.db", ["ical.h"]),

    ("../demos/zlib/lib.db", ["zlib.h"]),

    ("../demos/cgltf/lib.db", ["cgltf.h"]),

    ("../demos/jansson/lib.db", ["jansson.h", "value.c", "strbuffer.c", "load.c"]),
    """
]

run_test(tasks[0])

#Had to do it in separate processes, some global state is persisting somewhere and crashing.
#for t in tasks:
#    print(f"\nTesting {t[0]}\n")
#    p = multiprocessing.Process(target=run_test, args=(t,))
#    p.start()
#    p.join()
