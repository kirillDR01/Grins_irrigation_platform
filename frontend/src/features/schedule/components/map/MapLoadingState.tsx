/**
 * MapLoadingState component - Loading spinner for map data.
 */

import { Card, CardContent } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';

export function MapLoadingState() {
  return (
    <Card data-testid="map-loading" className="h-[500px]">
      <CardContent className="flex flex-col items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
        <p className="text-sm text-muted-foreground">Loading map...</p>
      </CardContent>
    </Card>
  );
}
