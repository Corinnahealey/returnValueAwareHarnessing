import multiprocessing
import process_mx
import engine
import matplotlib.pyplot as plt
import extractRetvals as extract
import os
import collections

def test_library(index, headers, name_and_expected):
    idx = process_mx.Index_Target_Header(index, headers, False)
    function_list, macros, enums, fps, aliases = idx.extractArtifacts()
    compatibility = engine.CheckCompatibility(idx.index, aliases, enums, "", False, False)
    functions = engine.APIfunctions()
    compatibility.process_functions(functions, function_list, "")

    funcs = functions.getAllFunctions()
    compatibility.checkrets(funcs)

    global tests_total
    global fail_total

    fail_count = 0
    for name, expected, retval in name_and_expected:
        target = next((f for f in funcs if f.name == name), None)

        if target.ret_status_check == expected:
            print(f"{name} passed")
        else:
            print(f"{name} FAILED")
            print("Expected:")
            print(f"  {expected}")
            print("Actual:")
            print(f"  {target.ret_status_check}")
            fail_count += 1
            print("\n")
    print(f"{index}: {(len(name_and_expected)-fail_count)/len(name_and_expected) * 100}% passed.")

def collect_retvals(tasks):
    """
    For every (index, headers, name_and_expected) item in *tasks*:
      • runs ExtractLib(index) in its own subprocess
      • picks the N-th Retval (third field) for each function listed in
        name_and_expected
    Returns
      dict[str, dict]  # {function_name: Retval.to_dict()}
    """
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
        print(f"{index_path} - {name_expected[0][0]}")
        wanted = {name: idx for name, _exp, idx in name_expected}
        p = multiprocessing.Process(target=worker,
                                    args=(index_path, wanted, retvals))
        p.start()
        procs.append(p)

    for p in procs:
        p.join()

    return dict(retvals)

def plot_retval_stats(retvals: dict[str, dict], outdir="plots"):
    """
    Given {function_name: retval_dict}, saves PNG plots for the following fields:
    - depth
    - in_loop
    - in_conditional
    - is_var
    - is_callexpr
    - is_enum
    - error_func_called
    - callexprs_in_block

    Ignores None values. Saves files as <outdir>/<field>_distribution.png
    """
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
        plt.figure()
        if isinstance(values[0], bool):
            counter = collections.Counter(values)
            plt.bar([str(k) for k in counter.keys()], counter.values())
        else:
            bins = range(min(values), max(values) + 2)
            plt.hist(values, bins=bins, align='left', rwidth=0.8, edgecolor='black')
            
        plt.title(f"{key} distribution")
        plt.xlabel(key)
        plt.ylabel("Frequency")
        plt.tight_layout()
        outfile = os.path.join(outdir, f"{key}_distribution.png")
        plt.savefig(outfile)
        plt.close()

def run_test(args):
    try:
        test_library(*args)
    except Exception as e:
        print(e)

tasks = [
    ("../demos/lexbor/lib.db", ["document.h", "parser.h", "unicode.h"], [
        ("lxb_html_parser_init", ("!=", "0"), 3),
        ("lxb_html_parser_destroy", ("!", None), 1),
        ("lxb_html_parser_ref", ("!", None), 1),
        ("lxb_html_parser_unref", ("!", None), 1),
        ("lxb_html_parse", ("!", None), 1),
        ("lxb_html_parse_fragment", ("!", None), 0),
        ("lxb_html_parse_fragment_by_tag_id", ("!", None), 2),
        ("lxb_html_parse_fragment_chunk_begin", ("!=", "0"), 1),
        ("lxb_html_parse_fragment_chunk_process", ("!=", "0"), 1),
        ("lxb_html_parse_fragment_chunk_end", ("!", None), 1),
        ("lxb_html_parse_chunk_begin", ("!", None), 2),
        ("lxb_html_parse_chunk_process", ("!=", "0"), 1),
        ("lxb_html_parse_chunk_end", ("!=", "0"), 1),
        ("lxb_html_parser_tree_noi", ("!", None), 0),
        ("lxb_html_parser_status_noi", ("!=", "0"), 0),
        ("lxb_html_parser_scripting_noi", (">", "0"), 0),
        ("lxb_unicode_idna_type", ("!=", "0"), 1),
        ("lexbor_mem_init", "[2, 3] U [9, 9]"),
        ("lexbor_bst_init", ""),
        ("lexbor_array_init", "[2, 3] U [5, 5]"),
        ("lexbor_dobject_init", "[2, 3] U [7, 7] U [9,9]"),
    ]),

    #These are wrappers. No sense in figuring out which return stmt at the moment.
    #("../demos/geos/lib.db", ["geos_c.h"], [
    #    ("GEOSSegmentIntersection", ("==", "0")),
    #    ("GEOSSnap", ("!", None)),
    #    ("GEOSSTRtree_build", ("!=", "1")),
    #    ("GEOSArea", ("!=", "1")),
    #    ("GEOSSymDifference", ("!", None)),
    #    ("GEOSUnaryUnion_r", ("!", None)),
    #    ("GEOSVoronoiDiagram", ("!", None)),
    #    ("GEOSWKBReader_read", ("!", None)),
    #    ("GEOSWKTWriter_write", ("!", None)),
    #    ("GEOSWKBReader_readHEX", ("!", None)),
    #    ("GEOSWithin", ("==", "2'")),
    #    ("GEOSUnion", ("!", None)),
    #    ("GEOSSymDifference_r", ("!", None)),
    #    ("GEOSSTRtree_remove", ("==", "2")),
    #    ("GEOSSTRtree_nearest_generic_r", ("!", None)),
    #    ("GEOSSTRtree_nearest_r", ("!", None)),
    #    ("GEOSSymDifference_r", ("!", None)),
    #    ("GEOSRelatePattern_r", ("==", "2")),
    #    ("GEOSRelateBoundaryNodeRule_r", ("!", None)),
    #    ("GEOSPreparedIntersectsXY_r", ("==", "2")),
    #    ("GEOSPreparedIntersects_r", ("==", "2")),
    #    ("GEOSPreparedDistance_r", ("!=", "1")),
    #    ("GEOSBufferParams_setJoinStyle_r", ("!=", "1")),
    #    ("GEOSBufferParams_setMitreLimit_r", ("!=", "1")),
    #    ("GEOSBufferParams_setQuadrantSegments_r", ("!=", "1")),
    #]),

    ("../demos/sqlite/lib.db", ["sqlite3.h"], [
        ("sqlite3_initialize", ("!=", "0"), 3), #This one depends on compiler flags. Figure out how our sqlite is built.
        ("sqlite3_shutdown", ("!=", "0"), 0), #Same with this one. TODO: Fix
        ("sqlite3_config", ("!=", "0"), 1),
        ("sqlite3_db_config", ("!=", "0"), 0),
        ("sqlite3_extended_result_codes", ("!=", "0"), 1),
        ("sqlite3_open", ("!=", "0"), 0),
        ("sqlite3_open_v2", ("!=", "0"), 0),
        ("sqlite3_open16", ("!=", "0"), 2),
        ("sqlite3_exec", ("!=", "0"), 1),
        ("sqlite3_reset", ("!=", "0"), 0),
        ("sqlite3_finalize", ("!=", "0"), 0),
        ("sqlite3_prepare_v3", ("!=", "0"), 0),
        ("sqlite3_stmt_explain", ("!=", "0"), 1), #TODO: figure out which build we have. Clang-check doesn't work here.
        ("sqlite3_bind_int", ("!=", "0"), 0),
        ("sqlite3_bind_text", ("!=", "0"), 0),
        ("sqlite3_complete", (">", "1"), 1), #TODO: same here
        ("sqlite3_complete16", (">", "1"), 1), #TODO: same here
        ("sqlite3_table_column_metadata", ("!=", "0"), 1), #TODO: same here
        ("sqlite3_file_control", ("!=", "0"), 1), #TODO: same here
        ("sqlite3_load_extension", ("!=", "0"), 0),
        ("sqlite3_enable_load_extension", ("!=", "0"), 1), #TODO: same here
        ("sqlite3_unlock_notify", ("!=", "0"), 1), #TODO: same here
        ("sqlite3_blob_open", ("!=", "0"), 2), #TODO: same here
        ("sqlite3_blob_read", ("!=", "0"), 0),
        ("sqlite3_blob_write", ("!=", "0"), 0),
    ]),

    #("../demos/pcre2/lib.db", ["pcre2.h"], [
    #    ("pcre2_callout_enumerate", ("!=", "0")),
    #    ("pcre2_compile", ("!", None)),
    #    ("pcre2_compile_context_copy", ("!", None)),
    #    ("pcre2_compile_context_create", ("!", None)),
    #    ("pcre2_config", ("<", "0")),
    #    ("pcre2_convert_context_copy", ("!", None)),
    #    ("pcre2_convert_context_create", ("!", None)),
    #    ("pcre2_dfa_match", (">", "-1")),
    #    ("pcre2_general_context_copy", ("!", None)),
    #    ("pcre2_general_context_create", ("!", None)),
    #    ("pcre2_get_error_message", ("<", "0")),
    #    ("pcre2_jit_compile", ("!=", "0")),
    #    ("pcre2_jit_stack_create", ("!", None)),
    #    ("pcre2_maketables", ("!", None)),
    #    ("pcre2_match_context_create", ("!", None)),
    #    ("pcre2_match_context_copy", ("!", None)),
    #    ("pcre2_match_data_create", ("!", None)),
    #    ("pcre2_match_data_create_from_pattern", ("!", None)),
    #    ("pcre2_pattern_convert", ("<", "0")),
    #    ("pcre2_pattern_info", ("<", "0")),
    #    ("pcre2_serialize_decode", ("<", "0")),
    #    ("pcre2_serialize_encode", ("<", "0")),
    #])

    
]

run_test(tasks[0])


#Had to do it in separate processes, some global state is persisting somewhere and crashing.
#for t in tasks:
#    print(f"\nTesting {t[0]}\n")
#    p = multiprocessing.Process(target=run_test, args=(t,))
#    p.start()
#    p.join()