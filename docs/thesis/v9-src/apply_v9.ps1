# Dựng chuong3-v9.docx từ v8: Phần B của kế hoạch docs/plans/43-thesis-ch3-reorder.md
#  B1  Mục 3.5 (phương pháp nghiên cứu, quy trình thực hiện) -> Chương 1, Mục 1.5
#  B2  Bảng 3.12 (thử nghiệm kỹ thuật) -> Chương 4, Mục 4.6.2
#  B3  Liên kết use case đăng nhập (Chương 3) với trình tự đăng nhập (Chương 4)
#  B4  Lớp gọi mô hình dùng chung + Hình 3.18 -> Chương 4, Mục 4.1.5
#  B5  Mỗi mục thiết kế ở 4.2-4.4 nói rõ nó chi tiết hóa use case nào (Mục, Bảng ở Chương 3)
# Sau khi chuyển: tự đánh lại số tiêu đề, số Hình/Bảng (trường SEQ), mọi tham chiếu "Hình/Bảng/Mục x.y" trong bài (theo tên chú thích/tiêu đề) và số trích dẫn IEEE.
# Dùng: powershell -NoProfile -ExecutionPolicy Bypass -File apply_v9.ps1   (PowerShell 5.1, tệp UTF-8 BOM)
param(
  [string]$Src = (Join-Path $PSScriptRoot '..\Khoa-luan-Le-Dang-Tan-11236199-chuong3-v8.docx'),
  [string]$Dst = (Join-Path $PSScriptRoot '..\Khoa-luan-Le-Dang-Tan-11236199-chuong3-v9.docx'),
  [string]$Log = (Join-Path $PSScriptRoot 'apply.log')
)
$ErrorActionPreference = 'Stop'
$Src = [IO.Path]::GetFullPath($Src); $Dst = [IO.Path]::GetFullPath($Dst)
$logLines = New-Object System.Collections.Generic.List[string]
$script:errors = 0
function L([string]$m) { $logLines.Add($m); Write-Host $m }
function Fail([string]$m) { $script:errors++; L "ERROR $m" }

Copy-Item $Src $Dst -Force
$word = New-Object -ComObject Word.Application
$word.Visible = $false; $word.DisplayAlerts = 0
$doc = $word.Documents.Open($Dst, $false, $false, $false)
$doc.TrackRevisions = $false

function Get-BodyStart {
  $b = 0
  foreach ($t in $doc.TablesOfContents) { if ($t.Range.End -gt $b) { $b = $t.Range.End } }
  foreach ($t in $doc.TablesOfFigures) { if ($t.Range.End -gt $b) { $b = $t.Range.End } }
  return $b
}
$script:bodyStart = Get-BodyStart
L "bodyStart=$script:bodyStart"

function Find-Range([string]$snippet) {
  $r = $doc.Range($script:bodyStart, $doc.Content.End)
  $f = $r.Find; $f.ClearFormatting(); $f.Text = $snippet; $f.Forward = $true; $f.Wrap = 0
  $f.MatchCase = $true; $f.MatchWildcards = $false
  if ($f.Execute()) { return $r }
  return $null
}
function Find-Para([string]$snippet) {
  $r = Find-Range $snippet
  if ($null -eq $r) { Fail "not found: $snippet"; return $null }
  return $r.Paragraphs.Item(1)
}
function Set-ParaText($p, [string]$text) { $r = $p.Range; [void]$r.MoveEnd(1, -1); $r.Text = $text }
function Replace-One([string]$old, [string]$new) {
  $r = Find-Range $old
  if ($null -eq $r) { Fail "not found: $old"; return }
  $r.Text = $new; L "ok replace: $old"
}
# chèn bản sao (có định dạng) của một đoạn Range vào trước vị trí $pos
function Insert-Copy([int]$pos, $srcRange) {
  $ins = $doc.Range($pos, $pos)
  $ins.FormattedText = $srcRange.FormattedText
}
# quét mọi đoạn sau phần mục lục: trả về danh sách {Start,Text,Level,InList}
function Scan-Paras {
  $res = New-Object System.Collections.Generic.List[object]
  $n = $doc.Paragraphs.Count
  for ($i = 1; $i -le $n; $i++) {
    $p = $doc.Paragraphs.Item($i)
    $r = $p.Range
    if ($r.Start -lt $script:bodyStart) { continue }
    $res.Add([pscustomobject]@{ Start = $r.Start; End = $r.End; Text = ($r.Text -replace "[\r\a]+$", ''); Level = [int]$p.OutlineLevel })
  }
  return $res
}
function Get-Info($paras) {
  $cap = @{}; $head = @{}
  $capOrder = New-Object System.Collections.Generic.List[string]
  foreach ($p in $paras) {
    if ($p.Text -match '^(Hình|Bảng) (\d+\.\d+)\. (.+)$') {
      $k = $Matches[3]
      if ($cap.ContainsKey($k)) { L "WARN duplicate caption text: $k" }
      $cap[$k] = "$($Matches[1]) $($Matches[2])"; $capOrder.Add($k)
    } elseif ($p.Level -ge 2 -and $p.Level -le 4 -and $p.Text -match '^(\d+(?:\.\d+)+)\. (.+)$') {
      if ($head.ContainsKey($Matches[2])) { L "WARN duplicate heading text: $($Matches[2])" }
      $head[$Matches[2]] = $Matches[1]
    }
  }
  return @{ Cap = $cap; Head = $head }
}
# áp dụng danh sách sửa (Start, End, New) từ cuối lên đầu
function Apply-Edits($edits, [string]$what) {
  $ok = 0
  foreach ($e in ($edits | Sort-Object { $_.Start } -Descending)) {
    $r = $doc.Range($e.Start, $e.End)
    if ($r.Text -ne $e.Old) { Fail "$what mismatch at $($e.Start): '$($r.Text)' != '$($e.Old)'"; continue }
    $r.Text = $e.New; $ok++
  }
  L "$what applied: $ok"
}

# =============== 0. ảnh chụp trạng thái cũ ===============
$p0 = Scan-Paras
$old = Get-Info $p0
$oldHeadByNum = @{}; foreach ($k in $old.Head.Keys) { $oldHeadByNum[$old.Head[$k]] = $k }
$oldCapByNum = @{}; foreach ($k in $old.Cap.Keys) { $oldCapByNum[$old.Cap[$k]] = $k }
L "snapshot: $($old.Cap.Count) captions, $($old.Head.Count) headings"

# =============== 1. nguồn các khối sẽ chuyển ===============
$h351 = Find-Para '3.5.1. Phương pháp nghiên cứu'
$p896 = Find-Para 'Hệ thống được xây dựng theo từng giai đoạn nhỏ'
$p897 = Find-Para 'Với những thành phần có rủi ro kỹ thuật cao'
$cap312 = Find-Para 'Các thử nghiệm kỹ thuật trước khi chốt thiết kế'
$h35 = Find-Para '3.5. Phương pháp và quy trình thực hiện'
$h36 = Find-Para '3.6. Kiến trúc hệ thống'
$p982 = Find-Para 'Mọi lời gọi mô hình ngôn ngữ đi qua một lớp dùng chung'
$cap318 = Find-Para 'Biểu đồ hoạt động của lớp gọi mô hình'
if ($script:errors -gt 0) { $doc.Close($false); if ($word.Documents.Count -eq 0) { $word.Quit() }; throw 'anchor missing' }
$tbl312 = $null
foreach ($t in $doc.Tables) { if ($t.Range.Start -gt $cap312.Range.End) { $tbl312 = $t; break } }
$blk1 = $doc.Range($h351.Range.Start, $p896.Range.End)
$blk2 = $doc.Range($p897.Range.Start, $tbl312.Range.End)
$blk3 = $doc.Range($p982.Range.Start, $cap318.Range.End)
$del35 = $doc.Range($h35.Range.Start, $h36.Range.Start)

# =============== 2. chèn bản sao vào chỗ mới ===============
# B1 -> Chương 1, trước "1.5. Ý nghĩa khoa học và thực tiễn"
$hy = Find-Para '1.5. Ý nghĩa khoa học và thực tiễn'
$pos = $hy.Range.Start
$lenHy = $hy.Range.End - $hy.Range.Start
Insert-Copy $pos $hy.Range          # bản sao tiêu đề đứng trước
Insert-Copy ($pos + $lenHy) $blk1    # rồi khối phương pháp, trước tiêu đề 1.5 cũ
$newH = $doc.Range($pos, $pos).Paragraphs.Item(1)
Set-ParaText $newH '1.5. Phương pháp nghiên cứu'
L 'B1 inserted into chapter 1'

# B2 -> Chương 4, trước "4.6.3. Dữ liệu thử nghiệm và số liệu vận hành"
$h463 = Find-Para '4.6.3. Dữ liệu thử nghiệm và số liệu vận hành'
Insert-Copy $h463.Range.Start $blk2
L 'B2 inserted into chapter 4'

# B4 -> Chương 4, mục 4.1.5 (trước "4.2. Thiết kế bước Lắng nghe")
$h42 = Find-Para '4.2. Thiết kế bước Lắng nghe'
$h414 = Find-Para '4.1.4. Bảo vệ thông tin và phân tách dữ liệu'
$pos = $h42.Range.Start
$lenH414 = $h414.Range.End - $h414.Range.Start
Insert-Copy $pos $h414.Range
Insert-Copy ($pos + $lenH414) $blk3
$newH2 = $doc.Range($pos, $pos).Paragraphs.Item(1)
Set-ParaText $newH2 '4.1.5. Lớp gọi mô hình dùng chung'
L 'B4 inserted into chapter 4'

# chú thích đã chép: đổi tiền tố chương (phần "Hình 3." / "Bảng 3." gõ tay)
foreach ($pair in @(@('Các thử nghiệm kỹ thuật trước khi chốt thiết kế', 'Bảng 3.', 'Bảng 4.'), @('Biểu đồ hoạt động của lớp gọi mô hình', 'Hình 3.', 'Hình 4.'))) {
  $hits = New-Object System.Collections.Generic.List[object]
  $r = $doc.Range($script:bodyStart, $doc.Content.End)
  $f = $r.Find; $f.ClearFormatting(); $f.Text = $pair[0]; $f.Forward = $true; $f.Wrap = 0; $f.MatchCase = $true
  while ($f.Execute()) { $hits.Add($r.Paragraphs.Item(1)); $r.Collapse(0) }
  # bản chép nằm ở Chương 4 (sau cùng); bản gốc ở Chương 3 sắp bị xóa
  $last = $hits[$hits.Count - 1]
  $pr = $last.Range
  $ff = $pr.Find; $ff.ClearFormatting()
  if ($ff.Execute($pair[1], $true, $false, $false, $false, $false, $true, 0, $false, $pair[2], 1)) { L "caption prefix: $($pair[0]) -> $($pair[2])" } else { Fail "caption prefix not changed: $($pair[0])" }
}

# =============== 3. xóa bản gốc ===============
$blk3.Delete() | Out-Null
$del35.Delete() | Out-Null
L 'originals deleted (3.5 and 3.6.4 model-call paragraph + figure)'

# =============== 4. cập nhật trường để số Hình/Bảng đúng ===============
[void]$doc.Fields.Update()
$script:bodyStart = Get-BodyStart

# =============== 5. đánh lại số tiêu đề ===============
$p1 = Scan-Paras
$chap = 0; $c2 = 0; $c3 = 0; $c4 = 0; $hEdits = New-Object System.Collections.Generic.List[object]
foreach ($p in $p1) {
  if ($p.Level -eq 1) {
    if ($p.Text -match '^CHƯƠNG (\d+)\.') { $chap = [int]$Matches[1]; $c2 = 0; $c3 = 0; $c4 = 0 } else { $chap = 0 }
    continue
  }
  if ($chap -eq 0 -or $p.Level -lt 2 -or $p.Level -gt 4) { continue }
  if ($p.Text -notmatch '^(\d+(?:\.\d+)+\.) ') { continue }
  $oldPref = $Matches[1]
  switch ($p.Level) {
    2 { $c2++; $c3 = 0; $c4 = 0; $new = "$chap.$c2." }
    3 { $c3++; $c4 = 0; $new = "$chap.$c2.$c3." }
    4 { $c4++; $new = "$chap.$c2.$c3.$c4." }
  }
  if ($new -ne $oldPref) { $hEdits.Add([pscustomobject]@{ Start = $p.Start; End = $p.Start + $oldPref.Length; Old = $oldPref; New = $new }) }
}
Apply-Edits $hEdits 'heading renumber'

# =============== 6. bản đồ mới và đánh lại tham chiếu Hình/Bảng/Mục ===============
$p2 = Scan-Paras
$new = Get-Info $p2
$refEdits = New-Object System.Collections.Generic.List[object]
$refHeadStart = 0
foreach ($p in $p2) { if ($p.Level -eq 1 -and $p.Text -eq 'TÀI LIỆU THAM KHẢO') { $refHeadStart = $p.Start; break } }
foreach ($p in $p2) {
  if ($p.Level -ge 1 -and $p.Level -le 4) { continue }
  if ($p.Text -match '^(Hình|Bảng) \d+\.\d+\. ') { continue }
  if ($refHeadStart -gt 0 -and $p.Start -ge $refHeadStart -and $p.Start -lt $refHeadStart + 100000 -and $p.Text -notmatch '(Hình|Bảng|Mục) \d') { continue }
  foreach ($m in [regex]::Matches($p.Text, '(Hình|Bảng|Mục) (\d+(?:\.\d+)+)')) {
    $kw = $m.Groups[1].Value; $num = $m.Groups[2].Value; $newNum = $null
    if ($kw -eq 'Mục') {
      if ($oldHeadByNum.ContainsKey($num)) { $key = $oldHeadByNum[$num]; if ($new.Head.ContainsKey($key)) { $newNum = $new.Head[$key] } else { Fail "Mục $num ($key) no longer exists" } }
      else { Fail "Mục $num not an old heading" }
    } else {
      $ref = "$kw $num"
      if ($oldCapByNum.ContainsKey($ref)) { $key = $oldCapByNum[$ref]; if ($new.Cap.ContainsKey($key)) { $newNum = ($new.Cap[$key] -replace '^\S+ ', '') } else { Fail "$ref ($key) no longer exists" } }
      else { Fail "$ref not an old caption" }
    }
    if ($null -ne $newNum -and $newNum -ne $num) {
      $s = $p.Start + $m.Groups[2].Index
      $refEdits.Add([pscustomobject]@{ Start = $s; End = $s + $num.Length; Old = $num; New = $newNum })
    }
  }
}
Apply-Edits $refEdits 'cross-reference renumber'

# =============== 7. trích dẫn IEEE: đánh lại theo thứ tự xuất hiện ===============
$p3 = Scan-Paras
$refHeadIdx = -1
for ($i = 0; $i -lt $p3.Count; $i++) { if ($p3[$i].Level -eq 1 -and $p3[$i].Text -eq 'TÀI LIỆU THAM KHẢO') { $refHeadIdx = $i; break } }
$phuLucIdx = -1
for ($i = $refHeadIdx + 1; $i -lt $p3.Count; $i++) { if ($p3[$i].Level -eq 1) { $phuLucIdx = $i; break } }
$order = New-Object System.Collections.Generic.List[int]
$citeEdits = New-Object System.Collections.Generic.List[object]
$citeHits = New-Object System.Collections.Generic.List[object]
for ($i = 0; $i -lt $refHeadIdx; $i++) {
  $p = $p3[$i]
  if ($p.Level -ge 1 -and $p.Level -le 4) { continue }
  foreach ($m in [regex]::Matches($p.Text, '\[(\d{1,2})\]')) {
    $n = [int]$m.Groups[1].Value
    if (-not $order.Contains($n)) { $order.Add($n) }
    $citeHits.Add([pscustomobject]@{ P = $p; Idx = $m.Groups[1].Index; N = $n; Len = $m.Groups[1].Length })
  }
}
$entries = @(); for ($i = $refHeadIdx + 1; $i -lt $phuLucIdx; $i++) { if ($p3[$i].Text.Length -gt 5) { $entries += $p3[$i] } }
L "citations: $($order.Count) distinct cited in body, $($entries.Count) reference entries"
$map = @{}; $k = 0; foreach ($n in $order) { $k++; $map[$n] = $k }
for ($n = 1; $n -le $entries.Count; $n++) { if (-not $map.ContainsKey($n)) { $k++; $map[$n] = $k; L "uncited reference kept at end: old [$n] -> [$k]" } }
foreach ($h in $citeHits) {
  $nn = $map[$h.N]
  if ($nn -ne $h.N) { $s = $h.P.Start + $h.Idx; $citeEdits.Add([pscustomobject]@{ Start = $s; End = $s + $h.Len; Old = "$($h.N)"; New = "$nn" }) }
}
Apply-Edits $citeEdits 'citation renumber'
# sắp lại danh sách tài liệu tham khảo (đánh số tự động theo thứ tự đoạn)
$changed = $false; for ($n = 1; $n -le $entries.Count; $n++) { if ($map[$n] -ne $n) { $changed = $true } }
if ($changed) {
  # các sửa [n] ở thân bài làm lệch vị trí: quét lại để lấy đúng vị trí các mục tham khảo
  $p3 = Scan-Paras
  $refHeadIdx = -1
  for ($i = 0; $i -lt $p3.Count; $i++) { if ($p3[$i].Level -eq 1 -and $p3[$i].Text -eq 'TÀI LIỆU THAM KHẢO') { $refHeadIdx = $i; break } }
  $phuLucIdx = -1
  for ($i = $refHeadIdx + 1; $i -lt $p3.Count; $i++) { if ($p3[$i].Level -eq 1) { $phuLucIdx = $i; break } }
  $entries = @(); for ($i = $refHeadIdx + 1; $i -lt $phuLucIdx; $i++) { if ($p3[$i].Text.Length -gt 5) { $entries += $p3[$i] } }
  $firstStart = $entries[0].Start
  $lastEnd = $entries[$entries.Count - 1].End
  $pos = $lastEnd                      # chép theo thứ tự mới vào ngay sau mục cuối, rồi xóa khối cũ bằng số vị trí
  $inv = @{}; foreach ($n in $map.Keys) { $inv[$map[$n]] = $n }
  for ($newNo = 1; $newNo -le $entries.Count; $newNo++) {
    $e = $entries[$inv[$newNo] - 1]
    $doc.Range($pos, $pos).FormattedText = $doc.Range($e.Start, $e.End).FormattedText
    $pos += ($e.End - $e.Start)
  }
  $doc.Range($firstStart, $lastEnd).Delete() | Out-Null
  L 'reference list reordered'
}

# =============== 8. câu nội dung mới (số hiệu cuối cùng, gõ sau khi đã đánh lại số) ===============
# B1: đoạn phương pháp đặt ở Chương 1
Replace-One 'qua bối cảnh ở Chương 1 và' 'qua bối cảnh ở Mục 1.1 và'
# B2
$pp = Find-Para 'Với những thành phần có rủi ro kỹ thuật cao'
if ($null -ne $pp) { Set-ParaText $pp 'Trước khi chốt thiết kế, đề tài viết thử nghiệm ngắn cho những thành phần có rủi ro kỹ thuật cao. Bảng 4.5 tóm tắt các thử nghiệm đó và quyết định rút ra. Đây là phép kiểm tra tính khả thi trên dữ liệu nhỏ hoặc giả lập, chưa phải số đo chất lượng của hệ thống hoàn chỉnh.'; L 'B2 lead-in rewritten' }
# B4: con trỏ ở Chương 3 và câu dẫn ở Chương 4
$pk = Find-Para 'Hệ thống vẫn giữ cách phân loại bằng mô hình ngôn ngữ thông thường làm phương án thay thế qua cấu hình'
if ($null -ne $pk) {
  $pos = $pk.Range.End
  $doc.Range($pos, $pos).FormattedText = $pk.Range.FormattedText
  $np = $doc.Range($pos, $pos).Paragraphs.Item(1)
  Set-ParaText $np 'Cách mọi lời gọi mô hình được thực hiện, gồm lược đồ JSON, đường dự phòng, thử lại và nhật ký lời gọi, được thiết kế ở Mục 4.1.5.'
  L 'B4 pointer added in chapter 3'
}
$pl = Find-Para 'Mọi lời gọi mô hình ngôn ngữ đi qua một lớp dùng chung'
if ($null -ne $pl) { $pl.Range.InsertBefore('Mục 3.5.4 cho biết mỗi tác vụ AI dùng mô hình nào; mục này mô tả cách mọi lời gọi đó được thực hiện. '); L 'B4 lead-in added in 4.1.5' }
# B3: liên kết đăng nhập
Replace-One 'Quá trình đăng ký được thể hiện ở Hình 3.6' 'Trình tự bên trong hai cách đăng nhập được thiết kế chi tiết ở Mục 4.1.4 (Hình 4.12 và Hình 4.13). Quá trình đăng ký được thể hiện ở Hình 3.6'
Replace-One 'Phiên đăng nhập là nền tảng của việc phân tách dữ liệu.' 'Phiên đăng nhập là nền tảng của việc phân tách dữ liệu; use case đăng nhập được đặc tả ở Bảng 3.5 (Mục 3.4.3) và phần này chi tiết hóa bên trong hai cách đăng nhập.'
# B5: mỗi mục thiết kế nói rõ chi tiết hóa use case nào
$b5 = @(
  @('4.2.1. Nhập dữ liệu và xác nhận ý nghĩa các cột', 'Phần này chi tiết hóa use case nhập tệp CSV và xác nhận ý nghĩa cột (Mục 3.4.4, Bảng 3.6). '),
  @('4.2.2. Xây dựng và cập nhật bộ chủ đề', 'Phần này chi tiết hóa use case sinh và áp dụng bộ chủ đề (Mục 3.4.5, Bảng 3.7). '),
  @('4.2.3. Phân loại phản hồi và tìm phản hồi tương tự', 'Phần này chi tiết hóa use case chạy phân loại phản hồi và tìm phản hồi tương tự (Mục 3.4.6, Bảng 3.8). '),
  @('4.2.4. Phân cụm và phát hiện biến động', 'Phần này chi tiết hóa use case chạy phân cụm (Mục 3.4.7, Bảng 3.9). '),
  @('4.3.2. Vòng điều tra có giới hạn', 'Từ mục này đến Mục 4.3.4 chi tiết hóa use case điều tra và duyệt nhận định (Mục 3.4.8, Bảng 3.10). '),
  @('4.4.1. Sinh phương án từ nhận định đã duyệt', 'Phần này chi tiết hóa use case sinh và chọn phương án (Mục 3.4.9, Bảng 3.11). ')
)
foreach ($b in $b5) {
  $h = Find-Para $b[0]
  if ($null -eq $h) { continue }
  $nx = $h.Next(1)
  if ($null -ne $nx -and [int]$nx.OutlineLevel -eq 10 -and $nx.Range.Text.Length -gt 40 -and $nx.Range.InlineShapes.Count -eq 0) { $nx.Range.InsertBefore($b[1]); L "B5 added under $($b[0])" }
  else { Fail "B5 next paragraph not plain text under $($b[0])" }
}
# bố cục / lời dẫn chương
Replace-One 'xác định mục tiêu, đối tượng, phạm vi nghiên cứu và đóng góp của đề tài' 'xác định mục tiêu, đối tượng, phạm vi, phương pháp nghiên cứu và đóng góp của đề tài'
Replace-One 'phân tích use case, phương pháp thực hiện và kiến trúc tổng thể' 'phân tích use case và kiến trúc tổng thể'
Replace-One 'phân tích use case, nêu phương pháp thực hiện và kiến trúc tổng thể' 'phân tích use case và kiến trúc tổng thể'

# =============== 9. cập nhật trường, mục lục, danh mục ===============
[void]$doc.Fields.Update()
foreach ($t in $doc.TablesOfContents) { $t.Update() }
foreach ($t in $doc.TablesOfFigures) { $t.Update() }
$doc.Repaginate()
L "pages=$($doc.ComputeStatistics(2)) errors=$script:errors"
$doc.Save()
$doc.Close($false)
if ($word.Documents.Count -eq 0) { $word.Quit() }
$logLines | Set-Content -Encoding UTF8 $Log
