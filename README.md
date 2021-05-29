# plotboss: a Chia plotting manager

![The view of plotboss](https://github.com/zeaphoo/plotboss/blob/main/docs/images/plotboss-0.1.png?raw=true "View")

This is a tool for managing [Chia](https://github.com/Chia-Network/chia-blockchain)
plotting operations.  The tool runs on the plotting machine and provides
the following functionality:

- Automatic spawning of new plotting jobs, possibly overlapping ("staggered")
  on multiple temp directories,  by per-temp-dir
limits.

- Monitoring of ongoing plotting and archiving jobs, progress, resources used,
  temp files, etc.

plotboss is designed for the following configuration:

- A plotting machine with an array of `tmp` dirs, a single `tmp2` dir, and an
  array of `dst` dirs to which the plot jobs plot.  The `dst` dirs serve as a
temporary buffer space for generated plots.

- A farming machine with a large number of drives, made accessible via an
  `rsyncd` module, and to be entirely populated with plots.  These are known as
the `archive` directories.

- Plot jobs are run with STDOUT/STDERR redirected to a log file in a configured
directory.  This allows analysis of progress (plot phase) as well as timing
(e.g. for analyzing performance).

## Functionality

plotboss tools are stateless.  Rather than keep an internal record of what jobs
have been started, plotboss relies on the process tables, open files, and
logfiles of plot jobs to understand "what's going on".  This means the tools
can be stopped and started, even from a different login session, without loss
of information.  It also means plotboss can see and manage jobs started manually
or by other tools, as long as their STDOUT/STDERR redirected to a file in a
known logfile directory.  (Note: The tool relies on reading the chia plot
command line arguments and the format of the plot tool output.  Changes in
those may break this tool.)

Plot scheduling is done by waiting for a certain amount of wall time since the
last job was started, finding the best (e.g. least recently used) `tmp` dir for
plotting, and ensuring that job has progressed to at least a certain point
(e.g., phase 2, subphase 5).

Plots are output to the `dst` dirs, which serve as a temporary buffer until they
are rsync'd ("archived") to the farmer/harvester.  The archiver does several
things to attempt to avoid concurrent IO.  First, it only allows one rsync
process at a time (more sophisticated scheduling could remove this
restriction, but it's nontrivial).  Second, it inspects the pipeline of plot
jobs to see which `dst` dirs are about to have plots written to them.  This
is balanced against how full the `dst` drives are in a priority scheme.
