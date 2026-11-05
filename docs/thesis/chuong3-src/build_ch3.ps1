param(
  [string]$Src, [string]$Dst, [string]$Json, [string]$ImgDir, [string]$Log, [string]$Pdf
)
$ErrorActionPreference = 'Stop'
$L = New-Object System.Collections.Generic.List[string]
function Log($m) { $script:L.Add($m) }

$items = Get-Content -Raw -Encoding UTF8 $Json | ConvertFrom-Json
Copy-Item $Src $Dst -Force

$w = New-Object -ComObject Word.Application
$w.Visible = $false
$w.DisplayAlerts = 0
$pre = $w.Documents.Count
Log "preexisting docs: $pre"
$d = $null
try {
  $d = $w.Documents.Open($Dst)
  $d.TrackRevisions = $false
  $Paras = $d.Paragraphs

  # ---- locate chapter 3 heading and KET LUAN heading
  $h1i = 0; $kli = 0
  $n = $Paras.Count
  for ($i = 1; $i -le $n; $i++) {
    $p = $Paras.Item($i)
    if ($p.OutlineLevel -ne 1) { continue }
    $sn = $p.Style.NameLocal
    if ($sn -notlike 'Heading 1*') { continue }
    $t = $p.Range.Text
    if ($h1i -eq 0 -and $t -like 'CH*NG 3.*') { $h1i = $i; continue }
    if ($h1i -gt 0) { $kli = $i; break }
  }
  Log "h1=$h1i kl=$kli"
  if ($h1i -eq 0 -or $kli -eq 0) { throw 'headings not found' }
  $h1 = $Paras.Item($h1i); $kl = $Paras.Item($kli)
  Log ("kl text: " + $kl.Range.Text.Trim())

  # ---- templates inside old chapter
  $tplBullet = $null; $tplEqG = $null; $tplEqP = $null
  for ($i = $h1i + 1; $i -lt $kli; $i++) {
    $p = $Paras.Item($i)
    $t = $p.Range.Text
    if (-not $tplBullet -and $p.Range.ListFormat.ListType -ne 0 -and $p.Range.Information(12) -eq $false) { $tplBullet = $p }
    if ($p.Range.OMaths.Count -gt 0) {
      if ($t -like '*(3.1)*') { $tplEqG = $p }
      if ($t -like '*(3.3)*') { $tplEqP = $p }
    }
  }
  $tplTbl = $null
  foreach ($tb in $d.Tables) {
    if ($tb.Range.Start -gt $h1.Range.End -and $tb.Range.Start -lt $kl.Range.Start) { $tplTbl = $tb; break }
  }
  if (-not ($tplBullet -and $tplEqG -and $tplEqP -and $tplTbl)) { throw 'template missing' }
  Log ("tplBullet: " + $tplBullet.Range.Text.Substring(0, 20))
  Log ("tplTbl first cell: " + $tplTbl.Cell(1,1).Range.Text)

  $oldStart = $h1.Range.End
  $newStart = $kl.Range.Start
  $secCount = $d.Range($oldStart, $newStart).Sections.Count
  Log "old range sections: $secCount"
  if ($secCount -ne 1) { throw 'old chapter range spans a section break' }

  $script:pos = $newStart

  function NewPara([string]$text) {
    $r = $d.Range($script:pos, $script:pos)
    $r.InsertBefore($text + "`r")
    $np = $d.Range($script:pos, $script:pos).Paragraphs.Item(1)
    return $np
  }
  function ResetTo($np, $styleConst) {
    $np.Range.Style = $d.Styles.Item($styleConst)
    $np.Range.ParagraphFormat.Reset()
    $np.Range.Font.Reset()
  }
  function CopyPara($tpl) {
    $r = $d.Range($script:pos, $script:pos)
    $r.FormattedText = $tpl.Range.FormattedText
    return $d.Range($script:pos, $script:pos).Paragraphs.Item(1)
  }

  $figCount = 0; $tblCount = 0
  foreach ($it in $items) {
    switch ($it.t) {
      'h2' { $np = NewPara $it.x; ResetTo $np 'Heading 2'; $np.KeepWithNext = -1; $script:pos = $np.Range.End }
      'h3' { $np = NewPara $it.x; ResetTo $np 'Heading 3'; $np.KeepWithNext = -1; $script:pos = $np.Range.End }
      'p'  {
        $np = NewPara $it.x; ResetTo $np 'Normal'
        $np.FirstLineIndent = 28
        $script:pos = $np.Range.End
      }
      'b' {
        $np = CopyPara $tplBullet
        $tr = $d.Range($np.Range.Start, $np.Range.End - 1)
        $tr.Text = $it.x
        $tr.Font.Bold = $false
        $np = $d.Range($script:pos, $script:pos).Paragraphs.Item(1)
        if ($it.bold) {
          $d.Range($np.Range.Start, $np.Range.Start + $it.bold.Length).Font.Bold = $true
        }
        $script:pos = $np.Range.End
      }
      'eq' {
        if ($it.tpl -eq 'G') { $np = CopyPara $tplEqG } else { $np = CopyPara $tplEqP }
        foreach ($f in $np.Range.Fields) {
          $code = $f.Code.Text
          if ($code -like '*TC *' -and $it.tpl -eq 'P') {
            $f.Code.Text = ' TC "Công thức 3.2. Điểm ưu tiên phương án" \f E '
          }
          if ($code -like '*SEQ CongThuc*') {
            if ($it.tpl -eq 'G') { $f.Code.Text = ' SEQ CongThuc \r 1 ' } else { $f.Code.Text = ' SEQ CongThuc ' }
          }
        }
        $np = $d.Range($script:pos, $script:pos).Paragraphs.Item(1)
        $script:pos = $np.Range.End
      }
      'fig' {
        $np = NewPara ''
        $np.Range.Style = $d.Styles.Item('HappyNest Figure')
        $np.Range.ParagraphFormat.Reset()
        $np.Range.Font.Reset()
        $s0 = $np.Range.Start
        $img = if ($it.img_path) { $it.img_path } else { Join-Path $ImgDir $it.img }
        $sh = $d.InlineShapes.AddPicture($img, $false, $true, $d.Range($s0, $s0))
        $sh.LockAspectRatio = -1
        $ratio = $sh.Height / $sh.Width
        $sh.Width = [single]$it.wpt
        $sh.Height = [single]($it.wpt * $ratio)
        $np = $d.Range($s0, $s0).Paragraphs.Item(1)
        $script:pos = $np.Range.End
        $figCount++
      }
      { $_ -eq 'capf' -or $_ -eq 'capt' } {
        if ($it.t -eq 'capf') { $lab = 'Hình'; $seq = 'Hình' } else { $lab = 'Bảng'; $seq = 'Bảng' }
        $np = NewPara ($lab + ' 3.. ' + $it.x)
        ResetTo $np 'Normal'
        $s0 = $np.Range.Start
        $code = 'SEQ ' + $seq + ' \* ARABIC \* MERGEFORMAT'
        if ($it.restart) { $code = 'SEQ ' + $seq + ' \r 1 \* ARABIC \* MERGEFORMAT' }
        [void]$d.Fields.Add($d.Range($s0 + 7, $s0 + 7), -1, $code, $false)
        $np = $d.Range($s0, $s0).Paragraphs.Item(1)
        $np.Range.Font.Bold = $true
        $np.Alignment = 1
        $np.FirstLineIndent = 0
        if ($it.t -eq 'capt') { $np.KeepWithNext = -1 } else { $np.KeepWithNext = 0 }
        $script:pos = $np.Range.End
      }
      'tbl' {
        $r = $d.Range($script:pos, $script:pos)
        $r.FormattedText = $tplTbl.Range.FormattedText
        $t = $d.Range($script:pos, $script:pos + 1).Tables.Item(1)
        $R = $it.rows.Count; $C = $it.rows[0].Count
        while ($t.Columns.Count -lt $C) { [void]$t.Columns.Add() }
        while ($t.Columns.Count -gt $C) { $t.Columns.Item($t.Columns.Count).Delete() }
        while ($t.Rows.Count -lt $R) { [void]$t.Rows.Add() }
        while ($t.Rows.Count -gt $R) { $t.Rows.Item($t.Rows.Count).Delete() }
        for ($j = 1; $j -le $C; $j++) {
          $t.Columns.Item($j).PreferredWidthType = 3
          $t.Columns.Item($j).PreferredWidth = [single]$it.w[$j - 1]
          $t.Columns.Item($j).Width = [single]$it.w[$j - 1]
        }
        for ($i = 1; $i -le $R; $i++) {
          for ($j = 1; $j -le $C; $j++) {
            $cell = $t.Cell($i, $j)
            $cell.Range.Text = ([string]$it.rows[$i - 1][$j - 1]).Replace("`n", "`r")
            if ($i -eq 1) {
              $cell.Range.Font.Bold = $true
              $cell.Shading.BackgroundPatternColor = 16051687
              $cell.VerticalAlignment = 1
            } else {
              $cell.Range.Font.Bold = $false
              $cell.Shading.BackgroundPatternColor = -16777216
              $cell.VerticalAlignment = 0
            }
          }
        }
        $t.Rows.Item(1).HeadingFormat = -1
        if ([string]$it.rows[0][0] -eq 'Tên use case') { for ($i = 2; $i -le $R; $i++) { $t.Cell($i, 1).Range.Font.Bold = $true } }
        if ($R -le 8) { for ($i = 1; $i -lt $R; $i++) { $t.Rows.Item($i).Range.ParagraphFormat.KeepWithNext = -1 } }
        $t.Borders.InsideLineStyle = 1
        $t.Borders.OutsideLineStyle = 1
        $t.Borders.InsideLineWidth = 4
        $t.Borders.OutsideLineWidth = 4
        $script:pos = $t.Range.End
        $tblCount++
      }
      default { throw ('unknown item type ' + $it.t) }
    }
  }
  Log "figs=$figCount tables=$tblCount newEnd=$($script:pos)"

  # ---- delete old chapter body
  $d.Range($oldStart, $newStart).Delete() | Out-Null
  Log "deleted old body"

  # ---- refresh numbering and lists
  [void]$d.Fields.Update()
  foreach ($toc in $d.TablesOfContents) { $toc.Update() }
  foreach ($tof in $d.TablesOfFigures) { $tof.Update() }
  [void]$d.Fields.Update()
  $d.Save()
  Log "saved $Dst"

  # ---- report pages of chapter 3
  $Paras = $d.Paragraphs
  $n = $Paras.Count
  for ($i = 1; $i -le $n; $i++) {
    $p = $Paras.Item($i)
    if ($p.OutlineLevel -eq 1 -and $p.Style.NameLocal -like 'Heading 1*') {
      $t = $p.Range.Text.Trim()
      Log ("H1 page {0}: {1}" -f $p.Range.Information(3), $t)
    }
  }
  if ($Pdf) { $d.ExportAsFixedFormat($Pdf, 17); Log "pdf $Pdf" }
} catch {
  Log ("ERROR: " + $_.Exception.Message + " @ " + $_.InvocationInfo.ScriptLineNumber)
} finally {
  if ($d) { $d.Close(0) }
  if ($w.Documents.Count -eq 0 -and $pre -eq 0) { $w.Quit() }
  [System.IO.File]::WriteAllLines($Log, $L, (New-Object System.Text.UTF8Encoding($false)))
}
