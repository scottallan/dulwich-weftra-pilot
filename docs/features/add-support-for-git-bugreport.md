# Feature Specification: `git bugreport` support in dulwich

## Status

Draft — no implementation exists yet. This document is the acceptance rubric
for that implementation and for its review.

## Source

- Upstream issue: jelmer/dulwich#1836, "Add support for git bugreport".
- Scope-defining clarification (verbatim intent, treated as authoritative for
  this spec): replicate C git's documented `git bugreport` command-line
  contract — default output file name/format, `--output-directory`, and
  `--suffix` should match what git documents; the report should collect the
  same *kinds* of information git's does (system/environment information and
  repository information) as far as dulwich can provide them. The
  `--diagnose` compressed-archive option is optional and, per this spec's
  decision below, is deferred (see "Out of scope").

## 1. What is being built and why

C git ships a `git bugreport` command that writes a single text file
combining (a) a fill-in-the-blanks template for the reporter to describe what
happened, and (b) automatically-collected system/environment and repository
information, so that bug reports are consistent and contain the diagnostic
context maintainers usually have to ask for separately.

dulwich currently has no equivalent. It does have `dulwich diagnose`
(`dulwich/cli.py`), which prints Python/dulwich version and dependency
information to the log, with a `# TODO: Support creating zip files with
diagnostic information` comment acknowledging it stops short of a full
bug-report tool. There is no repository-information counterpart at all, and
`diagnose` never writes a file — it only logs to stdout/stderr.

This feature adds a `dulwich bugreport` command that:

- Follows the same invocation contract as C git's `git bugreport` (default
  output filename pattern, `--output-directory`/`-o`, `--suffix`/`-s`), so
  that scripts, muscle memory, and documentation written against C git's
  `bugreport` continue to work when pointed at a dulwich checkout/installation.
  This is the stated motivation in the upstream issue ("generate standardized
  bug reports") and in the clarification that authorized this spec.
- Collects the same categories of information C git's report does —
  environment/system information and repository information — to the extent
  those categories are meaningful for a Python/dulwich installation, rather
  than reproducing every C-git-specific data point verbatim (e.g. libc
  version, compiler flags, or on-disk C-git-only structures do not have a
  dulwich analog and are not required).

This is the entirety of the intent. Anything not implied by "collect
information for bug reports" per the quoted issue is out of scope (see §4).

## 2. Command-line contract

The command MUST be invocable as `dulwich bugreport` and support the
following, matching what C git documents for `git bugreport`:

| Flag | Behavior |
|---|---|
| (none) | Writes a report file into the current working directory. Default filename is `git-bugreport-<suffix>.txt`, where `<suffix>` is the current local time formatted with the default suffix format `%Y-%m-%d-%H%M` (C git's documented default). Using the literal `git-bugreport-` filename prefix (not a `dulwich-`-branded prefix) is intentional: it is what makes the output recognizable to existing tooling/scripts/habits built around C git's command, per the clarification that authorized this spec. |
| `-o <path>`, `--output-directory <path>` | Writes the report file into `<path>` instead of the current working directory, keeping the same filename pattern. |
| `-s <format>`, `--suffix <format>` | Overrides the default `%Y-%m-%d-%H%M` suffix with a `strftime`-compatible format string, applied to the current local time. Resulting filename is still `git-bugreport-<formatted-suffix>.txt`. |
| `--diagnose[=<mode>]` | Not implemented in this feature. See §4. |

Notes that follow directly from replicating the documented contract:

- The command does not require write access to a git repository to run; it
  must work both inside and outside a repository, degrading gracefully
  (see §3) rather than erroring when run outside one.
- The report is written to a file by default — it is not printed to stdout
  by default, matching C git's behavior (`git bugreport` is a file-producing
  command, not a print-to-terminal command).
- Unwritable target directories/paths (e.g. `--output-directory` pointing at
  a nonexistent or permission-denied path) must produce a clear, non-zero-exit
  error rather than an unhandled traceback.

## 3. Report content requirements

The generated file MUST contain, at minimum, two kinds of sections, mirroring
the two things the issue asks for ("system and repository information"):

### 3.1 Reporter template section

A human-fillable section prompting the reporter for reproduction steps,
expected behavior, and actual behavior — analogous to C git's bug report
template header. Wording may be adapted to reference dulwich instead of C
git, but the structural intent (a template the user completes before sending
the report) must be preserved.

### 3.2 Automatically-collected information section(s)

Populated without user interaction, split conceptually into:

- **Environment/system information** — at minimum: dulwich version, Python
  version, Python executable path, and platform/OS information. This is
  materially the same information `dulwich diagnose` already collects; the
  bugreport's environment section must be at least as complete as what
  `dulwich diagnose` currently reports (version info, interpreter info,
  installed/optional dependency versions).
- **Repository information**, collected only when run inside a repository:
  at minimum, the current branch/HEAD state and a summary of working-tree
  status (e.g., counts or short summary of staged/unstaged/untracked
  changes — not full diffs or file contents). When run outside a repository,
  this section must be omitted or clearly marked as not applicable, without
  raising an unhandled error.

### 3.3 Privacy constraint (carried over from the documented C git behavior)

C git's own documentation is explicit that `bugreport` intentionally reports
*which* configuration/values are set, not their contents, to avoid leaking
sensitive data (e.g., it does not print credential-bearing remote URLs or
config values verbatim). This dulwich implementation MUST follow the same
principle: no secret-bearing values (credentials, tokens, full remote URLs
containing embedded credentials, raw config values that could contain
secrets) may be written into the report. Where a data point would risk
leaking such information, the report may note that the setting exists
without reproducing its value, or omit it.

## 4. Acceptance criteria

A change satisfies this spec if all of the following are independently
checkable and true:

1. `dulwich bugreport` is a registered CLI subcommand (discoverable via
   `dulwich --help` / the command listing), implemented following this
   repository's existing convention for exposing subcommands.
2. Running `dulwich bugreport` with no arguments, inside a repository,
   creates exactly one new file in the current working directory named
   `git-bugreport-<local-time formatted as %Y-%m-%d-%H%M>.txt`.
3. Running `dulwich bugreport --output-directory <dir>` writes the report
   into `<dir>` (which must already exist) using the same filename pattern,
   and does not also write a copy into the current working directory.
4. Running `dulwich bugreport --suffix <strftime-format>` produces a filename
   of `git-bugreport-<time formatted with the given format>.txt`.
5. `-o`/`-s` short flags work identically to their long forms.
6. The content of a generated report includes, at minimum: a reporter
   template section (§3.1), dulwich version, Python version, and Python
   executable path (§3.2).
7. When run inside a repository, the report additionally includes current
   branch/HEAD information and a working-tree status summary; the report
   never includes raw remote URLs, credentials, or raw config values (§3.3).
8. When run outside a repository (e.g., in a directory with no `.git`), the
   command still succeeds and produces a report containing the
   environment/system section, with the repository section omitted or marked
   not-applicable — it does not crash or print an unhandled traceback.
9. Writing to an invalid/unwritable output location fails with a clear error
   message and a non-zero process exit code, not a traceback.
10. The command and any new public API it relies on have test coverage
    added following this repository's existing testing conventions and
    locations for CLI commands (and for any new porcelain-level function, if
    one is introduced) — i.e., new tests live alongside the existing tests
    for comparable commands rather than in a new, differently-structured
    location.
11. The feature is recorded in the repository's existing top-level changelog
    file, following that file's existing entry format and current
    in-progress version section.
12. No behavior of any pre-existing command (including `dulwich diagnose`) is
    changed by this feature.

## 5. Out of scope

The following are explicitly **not** part of this feature. Absence of these
is not a defect against this spec:

- **`--diagnose` / compressed diagnostics archive.** C git's optional
  `--diagnose[=stats|all]` flag, which bundles a zip archive of additional
  low-level diagnostics (pack/object statistics, multi-pack-index,
  commit-graph state, sparse-checkout contents, hook file contents, etc.),
  is deferred and not required by this feature. Per the clarification that
  scoped this spec, it should be included only if it fits naturally; it does
  not fit naturally here because (a) several of the underlying data points
  it bundles (multi-pack-index status, commit-graph status, populated hook
  file contents, sparse-checkout state at that level of detail) have no
  existing dulwich equivalent to report today, and (b) archive/zip creation
  is a separate, independently-scoped capability that `dulwich diagnose`
  already flags as unimplemented future work (see its existing `# TODO:
  Support creating zip files with diagnostic information` comment). A future
  feature may add `--diagnose` once/if those prerequisites exist.
- Reporting on git-internal structures dulwich does not implement or does
  not maintain parity for, including but not limited to: multi-pack-index
  status, commit-graph status, populated Git hook contents/listing, and
  detailed sparse-checkout pattern dumps.
- Any network behavior: automatically submitting, uploading, or emailing the
  generated report anywhere. The command only ever writes a local file.
- Any interactive/GUI prompt flow for filling in the reporter template — the
  template is static text written into the file for the user to edit
  afterward, matching C git's behavior.
- Any output format other than the plain-text `.txt` report file (e.g. JSON,
  HTML).
- Localization/translation of the template or section headers.
- Changing, replacing, or removing the existing `dulwich diagnose` command
  or its current output contract.
- Adding new third-party runtime dependencies solely to gather additional
  system information; only information obtainable via the Python standard
  library and dulwich's own existing modules/dependencies is required.
