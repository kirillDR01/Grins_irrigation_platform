// Map a notification's subject_resource_type + id to a frontend route.
// Future-proof default returns '/'. The query-param form for appointment
// is a forward-looking hint — SchedulePage currently handles
// appointments inline; landing on /schedule is the right behavior today.
export function subjectRouteFor(type: string, id: string): string {
  switch (type) {
    case 'estimate':
      return `/estimates/${id}`;
    case 'appointment':
      return `/schedule?appointment=${id}`;
    default:
      return '/';
  }
}
