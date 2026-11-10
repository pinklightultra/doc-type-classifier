# Re-render from the repository root, with `doctype` on PATH:
#   vhs docs/demo/demo.tape
#
# The classify table's longest line is about 120 columns. Width and font size
# are set so that line fits without wrapping when the GIF is shown at GitHub's
# README width.

Output docs/demo/demo.gif

Require doctype

Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 14
Set LetterSpacing 0
Set LineHeight 1.2
Set Padding 14
Set Width 1080
Set Height 460
Set Framerate 12
Set TypingSpeed 35ms
Set Theme "GitHub Dark"
Set WindowBar Colorful
Set WindowBarSize 26

# Short prompt, off camera. Clear so the setup does not sit above the demo.
Hide
Type "export PS1='$ '"
Enter
Type "clear"
Enter
Show

Sleep 200ms
Type "doctype classify examples/docs/ --category-from-dir"
Enter
Sleep 4s
Type "doctype classify examples/docs/How-To/create-a-case.html --category-from-dir --explain"
Enter
Sleep 4s
