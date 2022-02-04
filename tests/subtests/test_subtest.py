import sys
import json
import shutil
import subprocess
from pathlib import Path

import matplotlib
import matplotlib.ft2font
from packaging.version import Version

from .helpers import assert_existence, diff_summary, patch_summary

# Handle Matplotlib and FreeType versions
MPL_VERSION = Version(matplotlib.__version__)
FTV = matplotlib.ft2font.__freetype_version__.replace('.', '')
VERSION_ID = f"mpl{MPL_VERSION.major}{MPL_VERSION.minor}_ft{FTV}"
HASH_LIBRARY = Path(__file__).parent / 'hashes' / (VERSION_ID + ".json")
RESULT_LIBRARY = Path(__file__).parent / 'result_hashes' / (VERSION_ID + ".json")
HASH_LIBRARY_FLAG = rf'--mpl-hash-library={HASH_LIBRARY}'
FULL_BASELINE_PATH = Path(__file__).parent / 'baseline'

BASELINE_IMAGES_FLAG = '--mpl-baseline-path=baseline'

TEST_FILE = Path(__file__).parent / 'subtest.py'

# Global settings to update baselines when running pytest
# Note: when updating baseline make sure you don't commit "fixes"
# for tests that are expected to fail
# (See also `run_subtest` argument `update_baseline` and `update_summary`.)
UPDATE_BASELINE = False  # baseline images and hashes
UPDATE_SUMMARY = False  # baseline summaries


def run_subtest(baseline_summary_name, tmp_path, args, summaries=None, xfail=True,
                update_baseline=UPDATE_BASELINE, update_summary=UPDATE_SUMMARY):
    """ Run pytest (within pytest) and check JSON summary report.

    Parameters
    ----------
    baseline_summary_name : str
        String of the filename without extension for the baseline summary.
    tmp_path : pathlib.Path
        Path of a temporary directory to store results.
    args : list
        Extra arguments to pass to pytest.
    summaries : tuple or list or set, optional, default=[]
        Summaries to generate in addition to `json`.
    xfail : bool, optional, default=True
        Whether the overall pytest run should fail.
    """
    # Parse arguments
    if summaries is None:
        summaries = []
    assert isinstance(summaries, (tuple, list, set))
    summaries = ','.join({'json'} | set(summaries))

    # Create the results path
    results_path = tmp_path / 'results'
    results_path.mkdir()

    # Configure the arguments to run the test
    pytest_args = [sys.executable, '-m', 'pytest', str(TEST_FILE)]
    mpl_args = ['--mpl', rf'--mpl-results-path={results_path.as_posix()}',
                f'--mpl-generate-summary={summaries}']
    if update_baseline:
        mpl_args += [rf'--mpl-generate-path={FULL_BASELINE_PATH}']
        if HASH_LIBRARY.exists():
            mpl_args += [rf'--mpl-generate-hash-library={HASH_LIBRARY}']

    # Run the test and record exit status
    status = subprocess.call(pytest_args + mpl_args + args)

    # If updating baseline, don't check summaries
    if update_baseline:
        assert status == 0
        if HASH_LIBRARY.exists():
            # Keep in sync. Use `git add -p` to commit specific lines.
            shutil.copy(HASH_LIBRARY, RESULT_LIBRARY)
        return

    # Ensure exit status is as expected
    if xfail:
        assert status != 0
    else:
        assert status == 0

    # Load summaries
    baseline_path = Path(__file__).parent / 'summaries'
    baseline_file = baseline_path / (baseline_summary_name + '.json')
    results_file = results_path / 'results.json'
    if update_summary:
        shutil.copy(results_file, baseline_file)
    with open(baseline_file, 'r') as f:
        baseline_summary = json.load(f)
    with open(results_file, 'r') as f:
        result_summary = json.load(f)

    # Apply version specific patches
    patch = baseline_path / (baseline_summary_name + f'_{VERSION_ID}.patch.json')
    if patch.exists():
        baseline_summary = patch_summary(baseline_summary, patch)
    # Note: version specific hashes should be handled by diff_summary instead

    # Compare summaries
    diff_summary(baseline_summary, result_summary,
                 baseline_hash_library=HASH_LIBRARY, result_hash_library=RESULT_LIBRARY)

    # Ensure reported images exist
    assert_existence(result_summary, path=results_path)


def test_default(tmp_path):
    run_subtest('test_default', tmp_path, [])


def test_hash(tmp_path):
    run_subtest('test_hash', tmp_path, [HASH_LIBRARY_FLAG])


def test_hybrid(tmp_path):
    run_subtest('test_hybrid', tmp_path, [HASH_LIBRARY_FLAG, BASELINE_IMAGES_FLAG])


def test_results_always(tmp_path):
    run_subtest('test_results_always', tmp_path,
                [HASH_LIBRARY_FLAG, BASELINE_IMAGES_FLAG, '--mpl-results-always'])


def test_html(tmp_path):
    run_subtest('test_results_always', tmp_path,
                [HASH_LIBRARY_FLAG, BASELINE_IMAGES_FLAG], summaries=['html'])
    assert (tmp_path / 'results' / 'fig_comparison.html').exists()
    assert (tmp_path / 'results' / 'extra.js').exists()
    assert (tmp_path / 'results' / 'styles.css').exists()


def test_html_hashes_only(tmp_path):
    run_subtest('test_html_hashes_only', tmp_path, [HASH_LIBRARY_FLAG], summaries=['html'])
    assert (tmp_path / 'results' / 'fig_comparison.html').exists()
    assert (tmp_path / 'results' / 'extra.js').exists()
    assert (tmp_path / 'results' / 'styles.css').exists()


def test_html_images_only(tmp_path):
    run_subtest('test_html_images_only', tmp_path, [], summaries=['html'])
    assert (tmp_path / 'results' / 'fig_comparison.html').exists()
    assert (tmp_path / 'results' / 'extra.js').exists()
    assert (tmp_path / 'results' / 'styles.css').exists()


def test_basic_html(tmp_path):
    run_subtest('test_results_always', tmp_path,
                [HASH_LIBRARY_FLAG, BASELINE_IMAGES_FLAG], summaries=['basic-html'])
    assert (tmp_path / 'results' / 'fig_comparison_basic.html').exists()
