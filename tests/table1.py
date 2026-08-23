"""The paper's published result tables, transcribed once.

This module is the single source of every number the project quotes from the
paper: the transcription tests check it, and `scripts/build_launch_entries.py`
builds the leaderboard's launch entries from it.  Nothing re-reads the PDF.

TABLE 1 -- benchmark-level comparison, pooled over three backbones
    metric -> method -> (three website marginals, six condition marginals,
    printed O/A).  Website order is GitLab / Magento / WordPress; condition
    order is src / src-perc / src-exec / tgt / tgt-perc / tgt-exec.
    `--` entries (AWM's ASC and SFR, which are undefined for prompted textual
    workflows) are omitted rather than encoded as zero.

TABLE 3 -- MPCR versus ASI over one fixed library, GPT-5 mini only
    metric -> method -> (six condition marginals, printed Average).  The table
    prints no website breakdown and no AS or SFR row, so those stay absent here
    rather than being invented; a leaderboard entry built from it carries an
    explicit null and a reason.
"""

TABLE1 = {
    "SR": {
        "AWM": ([17.71, 25.49, 62.66], [50.07, 43.35, 22.45, 41.28, 37.65, 16.90], 35.29),
        "ASI": ([20.81, 27.78, 60.27], [53.65, 48.80, 24.43, 41.84, 33.19, 15.79], 36.29),
        "SkillWeaver": ([13.78, 14.37, 32.29], [35.13, 28.75, 15.63, 17.80, 13.85, 9.71], 20.15),
        "WALT": ([21.07, 27.95, 55.38], [46.82, 43.53, 25.46, 41.17, 32.74, 19.09], 34.80),
    },
    "AS": {
        "AWM": ([8.03, 8.22, 4.76], [6.04, 6.32, 8.31, 6.34, 6.59, 8.44], 7.01),
        "ASI": ([7.87, 8.06, 4.73], [5.90, 5.95, 8.23, 6.29, 6.70, 8.24], 6.89),
        "SkillWeaver": ([14.79, 17.96, 12.63], [11.34, 13.48, 19.82, 12.59, 14.74, 18.80], 15.13),
        "WALT": ([12.39, 11.46, 8.53], [8.77, 9.92, 12.09, 10.66, 11.36, 11.96], 10.79),
    },
    "ASC": {
        "ASI": ([0.12, 0.19, 0.17], [0.18, 0.26, 0.29, 0.10, 0.10, 0.05], 0.16),
        "SkillWeaver": ([0.78, 0.63, 2.64], [1.13, 1.16, 1.14, 1.45, 1.50, 1.73], 1.35),
        "WALT": ([0.07, 0.19, 0.00], [0.05, 0.05, 0.21, 0.08, 0.03, 0.11], 0.09),
    },
    "SFR": {
        "ASI": ([19.55, 48.27, 16.26], [9.83, 24.85, 55.20, 13.53, 28.77, 35.98], 28.03),
        "SkillWeaver": ([4.61, 1.11, 0.21], [0.00, 0.41, 0.00, 2.03, 4.24, 5.17], 1.97),
        "WALT": ([48.52, 23.88, 0.00], [10.30, 23.29, 31.50, 23.28, 18.64, 37.76], 24.13),
    },
}

WEBSITES = ("gitlab", "magento", "wordpress")
CONDITIONS = ("src", "src-perc", "src-exec", "tgt", "tgt-perc", "tgt-exec")


def rows():
    """Yield (metric, method, websites_dict, conditions_dict, printed_overall)."""
    for metric, methods in TABLE1.items():
        for method, (websites, conditions, overall) in methods.items():
            yield (
                metric,
                method,
                dict(zip(WEBSITES, websites, strict=True)),
                dict(zip(CONDITIONS, conditions, strict=True)),
                overall,
            )


#: Table 3: MPCR versus ASI across transfer conditions, GPT-5 mini, one fixed
#: skill library.  metric -> method -> (six condition values, printed Average).
TABLE3 = {
    "SR": {
        "MPCR": ([56.67, 57.09, 33.23, 43.32, 37.24, 19.99], 41.26),
        "ASI": ([52.79, 53.02, 26.68, 42.83, 34.32, 17.75], 37.90),
    },
    "ASC": {
        "MPCR": ([0.22, 0.20, 0.19, 0.12, 0.14, 0.03], 0.15),
        "ASI": ([0.05, 0.13, 0.07, 0.04, 0.05, 0.02], 0.06),
    },
}

#: The backbone Table 3 was measured with.
TABLE3_MODEL = "gpt-5-mini"

#: Metrics Table 3 does not print.  Recorded so that an entry built from it says
#: why the value is null instead of leaving the reader to guess.
TABLE3_ABSENT_METRICS = ("AS", "SFR")


def table3_rows():
    """Yield (metric, method, conditions_dict, printed_average)."""
    for metric, methods in TABLE3.items():
        for method, (conditions, average) in methods.items():
            yield (metric, method, dict(zip(CONDITIONS, conditions, strict=True)), average)
