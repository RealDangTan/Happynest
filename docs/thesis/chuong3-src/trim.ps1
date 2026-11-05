param([string]$InDir, [string]$OutDir, [int]$Pad = 24, [int]$Dpi = 220)
$src = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class Trimmer {
  public static string Trim(string inPath, string outPath, int pad) {
    using (var bmp0 = new Bitmap(inPath)) {
      var bmp = new Bitmap(bmp0.Width, bmp0.Height, PixelFormat.Format32bppArgb);
      using (var g = Graphics.FromImage(bmp)) { g.Clear(Color.White); g.DrawImage(bmp0, 0, 0, bmp0.Width, bmp0.Height); }
      var rect = new Rectangle(0, 0, bmp.Width, bmp.Height);
      var data = bmp.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
      int stride = data.Stride; byte[] px = new byte[stride * bmp.Height];
      Marshal.Copy(data.Scan0, px, 0, px.Length); bmp.UnlockBits(data);
      int minX = bmp.Width, minY = bmp.Height, maxX = -1, maxY = -1;
      for (int y = 0; y < bmp.Height; y++) {
        int row = y * stride;
        for (int x = 0; x < bmp.Width; x++) {
          int i = row + x * 4;
          if (px[i] < 245 || px[i + 1] < 245 || px[i + 2] < 245) {
            if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
          }
        }
      }
      if (maxX < 0) { bmp.Save(outPath, ImageFormat.Png); return bmp.Width + "x" + bmp.Height; }
      minX = Math.Max(0, minX - pad); minY = Math.Max(0, minY - pad);
      maxX = Math.Min(bmp.Width - 1, maxX + pad); maxY = Math.Min(bmp.Height - 1, maxY + pad);
      var crop = new Rectangle(minX, minY, maxX - minX + 1, maxY - minY + 1);
      using (var outB = bmp.Clone(crop, PixelFormat.Format24bppRgb)) {
        outB.SetResolution(220, 220);
        outB.Save(outPath, ImageFormat.Png);
      }
      bmp.Dispose();
      return crop.Width + "x" + crop.Height;
    }
  }
}
"@
if (-not ("Trimmer" -as [type])) { Add-Type -TypeDefinition $src -ReferencedAssemblies System.Drawing }
New-Item -ItemType Directory -Force $OutDir | Out-Null
$rows = @()
foreach ($f in Get-ChildItem (Join-Path $InDir '*.png') | Sort-Object Name) {
  $o = Join-Path $OutDir $f.Name
  $sz = [Trimmer]::Trim($f.FullName, $o, $Pad)
  $w = [int]($sz.Split('x')[0]); $h = [int]($sz.Split('x')[1])
  $wpt = [Math]::Round($w / $Dpi * 72); $hpt = [Math]::Round($h / $Dpi * 72)
  $rows += ("{0},{1},{2},{3},{4}" -f $f.BaseName, $w, $h, $wpt, $hpt)
}
$rows | Set-Content -Encoding UTF8 (Join-Path $OutDir 'sizes.csv')
$rows
