# puzzicle

Tools related to crossword puzzles. Functionality includes:

* **puzshow** to print stats about a puzzle
* **puzedit** to produce .puz files from multiple input sources, such as qxw files and text files ontaining clues
* **puzrender** to render .puz files as HTML or PDF

## Install local launchers

Execute

    $ ant install

to make the programs available at `$HOME/.local/bin`. Python 3.6+ is required.

On subsequent builds, add `-Dinstall.overwrite=true` to allow the install script
to overwrite existing executables.