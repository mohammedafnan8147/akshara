using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Globalization;
using System.IO;
using System.Web.Script.Serialization;

namespace Akshara
{
    // Deterministic, offline renderer for realistic specimen forms.
    // Input is a simple JSON command list produced by tools/generate_samples.py.
    // Output is a PNG and measured text boxes for overlay alignment.
    public static class FormRenderer
    {
        private static JavaScriptSerializer Json = new JavaScriptSerializer();

        public static int Main(string[] args)
        {
            if (args.Length < 3)
            {
                Console.Error.WriteLine("usage: FormRenderer.exe <commands.json> <out.png> <meta.json>");
                return 2;
            }

            var spec = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(args[0]));
            int width = ToInt(spec["width"]);
            int height = ToInt(spec["height"]);
            string background = Str(spec, "background", "#FBF8F0");

            using (var bmp = new Bitmap(width, height, PixelFormat.Format32bppArgb))
            using (var g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = SmoothingMode.AntiAlias;
                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
                g.Clear(ColorFrom(background));

                var measured = new Dictionary<string, object>();
                var ops = AsList(spec["ops"]);
                foreach (var raw in ops)
                {
                    var op = (Dictionary<string, object>)raw;
                    string type = Str(op, "type", "");
                    string id = Str(op, "id", null);
                    float angle = ToFloat(op, "rotate", 0f);
                    Matrix saved = null;
                    if (Math.Abs(angle) > 0.001)
                    {
                        saved = g.Transform;
                        float cx = ToFloat(op, "cx", width / 2f);
                        float cy = ToFloat(op, "cy", height / 2f);
                        g.TranslateTransform(cx, cy);
                        g.RotateTransform(angle);
                        g.TranslateTransform(-cx, -cy);
                    }

                    try
                    {
                        switch (type)
                        {
                            case "rect":
                                DrawRect(g, op);
                                break;
                            case "line":
                                DrawLine(g, op);
                                break;
                            case "ellipse":
                                DrawEllipse(g, op);
                                break;
                            case "text":
                                var box = DrawText(g, op, id != null);
                                if (id != null && box != null)
                                {
                                    measured[id] = new Dictionary<string, object> {
                                        { "x", box.Value.X }, { "y", box.Value.Y },
                                        { "w", box.Value.Width }, { "h", box.Value.Height }
                                    };
                                }
                                break;
                            case "path":
                                DrawPath(g, op);
                                break;
                            case "bars":
                                DrawBars(g, op);
                                break;
                        }
                    }
                    finally
                    {
                        if (saved != null) g.Transform = saved;
                    }
                }

                bmp.Save(args[1], ImageFormat.Png);
                File.WriteAllText(args[2], Json.Serialize(measured));
            }
            return 0;
        }

        private static void DrawRect(Graphics g, Dictionary<string, object> op)
        {
            float x = ToFloat(op, "x", 0), y = ToFloat(op, "y", 0);
            float w = ToFloat(op, "w", 0), h = ToFloat(op, "h", 0);
            float r = ToFloat(op, "radius", 0);
            Color? fill = ColorOrNull(op, "fill");
            Color? stroke = ColorOrNull(op, "stroke");
            float sw = ToFloat(op, "width", 1);

            GraphicsPath path;
            if (r > 0)
            {
                path = RoundedRect(new RectangleF(x, y, w, h), r);
            }
            else
            {
                path = new GraphicsPath();
                path.AddRectangle(new RectangleF(x, y, w, h));
            }

            if (fill.HasValue)
                using (var b = new SolidBrush(fill.Value)) g.FillPath(b, path);
            if (stroke.HasValue)
                using (var p = new Pen(stroke.Value, sw)) g.DrawPath(p, path);
            path.Dispose();
        }

        private static void DrawLine(Graphics g, Dictionary<string, object> op)
        {
            float x1 = ToFloat(op, "x1", 0), y1 = ToFloat(op, "y1", 0);
            float x2 = ToFloat(op, "x2", 0), y2 = ToFloat(op, "y2", 0);
            Color color = ColorFrom(Str(op, "color", "#333333"));
            float width = ToFloat(op, "width", 1);
            using (var p = new Pen(color, width))
            {
                string dash = Str(op, "dash", null);
                if (dash == "dash") p.DashStyle = DashStyle.Dash;
                if (dash == "dot") p.DashStyle = DashStyle.Dot;
                p.StartCap = LineCap.Round;
                p.EndCap = LineCap.Round;
                g.DrawLine(p, x1, y1, x2, y2);
            }
        }

        private static void DrawEllipse(Graphics g, Dictionary<string, object> op)
        {
            float x = ToFloat(op, "x", 0), y = ToFloat(op, "y", 0);
            float w = ToFloat(op, "w", 0), h = ToFloat(op, "h", 0);
            Color? fill = ColorOrNull(op, "fill");
            Color? stroke = ColorOrNull(op, "stroke");
            float sw = ToFloat(op, "width", 1);
            if (fill.HasValue)
                using (var b = new SolidBrush(fill.Value)) g.FillEllipse(b, x, y, w, h);
            if (stroke.HasValue)
                using (var p = new Pen(stroke.Value, sw)) g.DrawEllipse(p, x, y, w, h);
        }

        private static RectangleF? DrawText(Graphics g, Dictionary<string, object> op, bool shouldMeasure)
        {
            string text = Str(op, "text", "");
            if (string.IsNullOrEmpty(text)) return null;

            float x = ToFloat(op, "x", 0), y = ToFloat(op, "y", 0);
            float w = ToFloat(op, "w", 1000), h = ToFloat(op, "h", 200);
            float size = ToFloat(op, "size", 20);
            string fontName = Str(op, "font", "Segoe UI");
            string style = Str(op, "style", "regular");
            bool rtl = ToBool(op, "rtl", false);
            bool wrap = ToBool(op, "wrap", false);
            string align = Str(op, "align", "left");
            string valign = Str(op, "valign", "top");
            Color color = ColorFrom(Str(op, "color", "#17211E"));

            FontStyle fs = FontStyle.Regular;
            if (style.IndexOf("bold", StringComparison.OrdinalIgnoreCase) >= 0) fs |= FontStyle.Bold;
            if (style.IndexOf("italic", StringComparison.OrdinalIgnoreCase) >= 0) fs |= FontStyle.Italic;

            Font font;
            try { font = new Font(fontName, size, fs, GraphicsUnit.Pixel); }
            catch { font = new Font("Segoe UI", size, fs, GraphicsUnit.Pixel); }

            var format = new StringFormat(StringFormat.GenericTypographic);
            format.FormatFlags |= StringFormatFlags.MeasureTrailingSpaces;
            if (!wrap) format.FormatFlags |= StringFormatFlags.NoWrap;
            if (rtl) format.FormatFlags |= StringFormatFlags.DirectionRightToLeft;
            if (align == "center") format.Alignment = StringAlignment.Center;
            else if (align == "right" || (rtl && align == "auto")) format.Alignment = StringAlignment.Far;
            else format.Alignment = StringAlignment.Near;
            if (valign == "center") format.LineAlignment = StringAlignment.Center;
            else if (valign == "bottom") format.LineAlignment = StringAlignment.Far;
            else format.LineAlignment = StringAlignment.Near;

            SizeF measuredSize;
            if (wrap)
                measuredSize = g.MeasureString(text, font, new SizeF(w, h), format);
            else
                measuredSize = g.MeasureString(text, font, new PointF(0, 0), format);

            if (shouldMeasure)
            {
                // Approximate the actual painted glyph box, accounting for alignment.
                float bx = x;
                if (format.Alignment == StringAlignment.Center) bx = x + (w - measuredSize.Width) / 2f;
                else if (format.Alignment == StringAlignment.Far) bx = x + w - measuredSize.Width;

                float by = y;
                if (format.LineAlignment == StringAlignment.Center) by = y + (h - measuredSize.Height) / 2f;
                else if (format.LineAlignment == StringAlignment.Far) by = y + h - measuredSize.Height;

                using (var brush = new SolidBrush(color))
                    g.DrawString(text, font, brush, new RectangleF(x, y, w, h), format);

                var result = new RectangleF(bx, by, Math.Max(2, measuredSize.Width), Math.Max(2, measuredSize.Height));
                font.Dispose();
                format.Dispose();
                return result;
            }

            using (var brush = new SolidBrush(color))
                g.DrawString(text, font, brush, new RectangleF(x, y, w, h), format);

            font.Dispose();
            format.Dispose();
            return null;
        }

        private static void DrawPath(Graphics g, Dictionary<string, object> op)
        {
            var ptsRaw = AsList(op["points"]);
            var pts = new PointF[ptsRaw.Count];
            for (int i = 0; i < ptsRaw.Count; i++)
            {
                var pair = AsList(ptsRaw[i]);
                pts[i] = new PointF(ToFloat(pair[0]), ToFloat(pair[1]));
            }
            if (pts.Length < 2) return;
            Color color = ColorFrom(Str(op, "color", "#243B36"));
            float width = ToFloat(op, "width", 2);
            using (var p = new Pen(color, width))
            {
                p.StartCap = LineCap.Round;
                p.EndCap = LineCap.Round;
                p.LineJoin = LineJoin.Round;
                if (pts.Length >= 4)
                {
                    for (int i = 0; i + 3 < pts.Length; i += 3)
                        g.DrawBezier(p, pts[i], pts[i + 1], pts[i + 2], pts[i + 3]);
                }
                else
                {
                    g.DrawLines(p, pts);
                }
            }
        }

        private static void DrawBars(Graphics g, Dictionary<string, object> op)
        {
            float x = ToFloat(op, "x", 0), y = ToFloat(op, "y", 0);
            float h = ToFloat(op, "h", 40);
            Color color = ColorFrom(Str(op, "color", "#222222"));
            var widths = AsList(op["widths"]);
            float cursor = x;
            foreach (var wr in widths)
            {
                float bw = ToFloat(wr);
                using (var b = new SolidBrush(color)) g.FillRectangle(b, cursor, y, bw, h);
                cursor += bw + 3;
            }
        }

        private static GraphicsPath RoundedRect(RectangleF r, float radius)
        {
            var p = new GraphicsPath();
            float d = radius * 2;
            p.AddArc(r.X, r.Y, d, d, 180, 90);
            p.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            p.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            p.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            p.CloseFigure();
            return p;
        }

        private static Color ColorFrom(string hex)
        {
            if (string.IsNullOrEmpty(hex)) return Color.Black;
            hex = hex.Trim();
            if (hex[0] == '#') hex = hex.Substring(1);
            if (hex.Length == 8)
            {
                int a = int.Parse(hex.Substring(0, 2), NumberStyles.HexNumber);
                int r = int.Parse(hex.Substring(2, 2), NumberStyles.HexNumber);
                int gg = int.Parse(hex.Substring(4, 2), NumberStyles.HexNumber);
                int b = int.Parse(hex.Substring(6, 2), NumberStyles.HexNumber);
                return Color.FromArgb(a, r, gg, b);
            }
            if (hex.Length == 6)
            {
                int r = int.Parse(hex.Substring(0, 2), NumberStyles.HexNumber);
                int gg = int.Parse(hex.Substring(2, 2), NumberStyles.HexNumber);
                int b = int.Parse(hex.Substring(4, 2), NumberStyles.HexNumber);
                return Color.FromArgb(255, r, gg, b);
            }
            return Color.Black;
        }

        private static Color? ColorOrNull(Dictionary<string, object> op, string key)
        {
            if (!op.ContainsKey(key) || op[key] == null) return null;
            string s = op[key].ToString();
            if (string.IsNullOrEmpty(s) || s == "none") return null;
            return ColorFrom(s);
        }

        private static string Str(Dictionary<string, object> d, string key, string fallback)
        {
            if (d.ContainsKey(key) && d[key] != null) return d[key].ToString();
            return fallback;
        }

        private static float ToFloat(Dictionary<string, object> d, string key, float fallback)
        {
            if (!d.ContainsKey(key) || d[key] == null) return fallback;
            return Convert.ToSingle(d[key], CultureInfo.InvariantCulture);
        }

        private static float ToFloat(object o)
        {
            return Convert.ToSingle(o, CultureInfo.InvariantCulture);
        }

        private static int ToInt(object o)
        {
            return Convert.ToInt32(o, CultureInfo.InvariantCulture);
        }

        private static bool ToBool(Dictionary<string, object> d, string key, bool fallback)
        {
            if (!d.ContainsKey(key) || d[key] == null) return fallback;
            if (d[key] is bool) return (bool)d[key];
            return d[key].ToString() == "1" || d[key].ToString().ToLowerInvariant() == "true";
        }

        private static System.Collections.IList AsList(object value)
        {
            if (value is System.Collections.IList) return (System.Collections.IList)value;
            return new object[0];
        }
    }
}
