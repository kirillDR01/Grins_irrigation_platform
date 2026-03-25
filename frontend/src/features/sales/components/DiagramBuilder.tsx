import { useRef, useState, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Square,
  Circle,
  Minus,
  Type,
  Droplets,
  Save,
  Upload,
  Trash2,
  Undo2,
} from 'lucide-react';
import { toast } from 'sonner';

type Tool = 'select' | 'rectangle' | 'circle' | 'line' | 'text' | 'sprinkler' | 'pipe' | 'valve';

interface CanvasElement {
  id: string;
  type: Tool;
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
}

const TOOLS: { id: Tool; icon: React.ReactNode; label: string }[] = [
  { id: 'rectangle', icon: <Square className="h-4 w-4" />, label: 'Rectangle' },
  { id: 'circle', icon: <Circle className="h-4 w-4" />, label: 'Circle' },
  { id: 'line', icon: <Minus className="h-4 w-4" />, label: 'Line' },
  { id: 'text', icon: <Type className="h-4 w-4" />, label: 'Text' },
];

const IRRIGATION_ICONS: { id: Tool; icon: React.ReactNode; label: string }[] = [
  { id: 'sprinkler', icon: <Droplets className="h-4 w-4" />, label: 'Sprinkler' },
  { id: 'pipe', icon: <Minus className="h-4 w-4 rotate-45" />, label: 'Pipe' },
  { id: 'valve', icon: <Circle className="h-3 w-3" />, label: 'Valve' },
];

export function DiagramBuilder() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeTool, setActiveTool] = useState<Tool>('select');
  const [elements, setElements] = useState<CanvasElement[]>([]);
  const [backgroundImage, setBackgroundImage] = useState<HTMLImageElement | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });

  // Draw all elements on canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background
    if (backgroundImage) {
      ctx.drawImage(backgroundImage, 0, 0, canvas.width, canvas.height);
    } else {
      ctx.fillStyle = '#f8fafc';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      // Grid
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 0.5;
      for (let x = 0; x < canvas.width; x += 20) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 20) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }
    }

    // Elements
    elements.forEach((el) => {
      ctx.strokeStyle = '#0d9488';
      ctx.fillStyle = '#ccfbf1';
      ctx.lineWidth = 2;

      switch (el.type) {
        case 'rectangle':
          ctx.fillRect(el.x, el.y, el.width, el.height);
          ctx.strokeRect(el.x, el.y, el.width, el.height);
          break;
        case 'circle':
          ctx.beginPath();
          ctx.ellipse(el.x + el.width / 2, el.y + el.height / 2, Math.abs(el.width / 2), Math.abs(el.height / 2), 0, 0, Math.PI * 2);
          ctx.fill(); ctx.stroke();
          break;
        case 'line':
          ctx.beginPath();
          ctx.moveTo(el.x, el.y);
          ctx.lineTo(el.x + el.width, el.y + el.height);
          ctx.stroke();
          break;
        case 'text':
          ctx.fillStyle = '#0f172a';
          ctx.font = '14px sans-serif';
          ctx.fillText(el.label || 'Text', el.x, el.y + 14);
          break;
        case 'sprinkler':
          ctx.fillStyle = '#0d9488';
          ctx.beginPath();
          ctx.arc(el.x, el.y, 8, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = '#fff';
          ctx.font = '8px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('S', el.x, el.y + 3);
          ctx.textAlign = 'start';
          break;
        case 'pipe':
          ctx.strokeStyle = '#0d9488';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.moveTo(el.x, el.y);
          ctx.lineTo(el.x + el.width, el.y + el.height);
          ctx.stroke();
          ctx.lineWidth = 2;
          break;
        case 'valve':
          ctx.fillStyle = '#f59e0b';
          ctx.beginPath();
          ctx.arc(el.x, el.y, 6, 0, Math.PI * 2);
          ctx.fill();
          ctx.strokeStyle = '#92400e';
          ctx.stroke();
          break;
      }
    });
  }, [elements, backgroundImage]);

  useEffect(() => { draw(); }, [draw]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (activeTool === 'select') return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (['sprinkler', 'pipe', 'valve', 'text'].includes(activeTool)) {
      setElements((prev) => [...prev, {
        id: crypto.randomUUID(),
        type: activeTool,
        x, y,
        width: 0, height: 0,
        label: activeTool === 'text' ? 'Label' : undefined,
      }]);
      return;
    }

    setIsDrawing(true);
    setStartPos({ x, y });
  };

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setElements((prev) => [...prev, {
      id: crypto.randomUUID(),
      type: activeTool,
      x: Math.min(startPos.x, x),
      y: Math.min(startPos.y, y),
      width: x - startPos.x,
      height: y - startPos.y,
    }]);
    setIsDrawing(false);
  };

  const handleBackgroundImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const img = new Image();
    img.onload = () => setBackgroundImage(img);
    img.src = URL.createObjectURL(file);
  };

  const handleSaveAsPng = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = 'diagram.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
    toast.success('Diagram saved as PNG');
  };

  return (
    <Card data-testid="diagram-builder">
      <CardHeader>
        <CardTitle className="text-lg">Property Diagram Builder</CardTitle>
        <p className="text-sm text-slate-500">Draw irrigation system layouts for estimates</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 border rounded-lg p-1">
            {TOOLS.map((tool) => (
              <Button
                key={tool.id}
                variant={activeTool === tool.id ? 'default' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => setActiveTool(tool.id)}
                title={tool.label}
                data-testid={`tool-${tool.id}`}
              >
                {tool.icon}
              </Button>
            ))}
          </div>

          <div className="h-6 w-px bg-slate-200" />

          {/* Irrigation icons */}
          <div className="flex items-center gap-1 border rounded-lg p-1">
            {IRRIGATION_ICONS.map((icon) => (
              <Button
                key={icon.id}
                variant={activeTool === icon.id ? 'default' : 'ghost'}
                size="icon"
                className="h-8 w-8"
                onClick={() => setActiveTool(icon.id)}
                title={icon.label}
                data-testid={`tool-${icon.id}`}
              >
                {icon.icon}
              </Button>
            ))}
          </div>

          <div className="h-6 w-px bg-slate-200" />

          {/* Actions */}
          <Button variant="outline" size="sm" onClick={() => setElements((prev) => prev.slice(0, -1))} data-testid="undo-btn">
            <Undo2 className="h-4 w-4 mr-1" /> Undo
          </Button>
          <Button variant="outline" size="sm" onClick={() => setElements([])} data-testid="clear-btn">
            <Trash2 className="h-4 w-4 mr-1" /> Clear
          </Button>

          <div className="ml-auto flex items-center gap-2">
            <Label className="text-xs cursor-pointer">
              <Input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleBackgroundImport}
                data-testid="bg-import-input"
              />
              <Button variant="outline" size="sm" asChild>
                <span><Upload className="h-4 w-4 mr-1" /> Background</span>
              </Button>
            </Label>
            <Button size="sm" onClick={handleSaveAsPng} data-testid="save-png-btn">
              <Save className="h-4 w-4 mr-1" /> Save PNG
            </Button>
          </div>
        </div>

        {/* Canvas */}
        <div className="border rounded-lg overflow-hidden">
          <canvas
            ref={canvasRef}
            width={800}
            height={500}
            className="w-full cursor-crosshair"
            onMouseDown={handleMouseDown}
            onMouseUp={handleMouseUp}
            data-testid="diagram-canvas"
          />
        </div>
      </CardContent>
    </Card>
  );
}
