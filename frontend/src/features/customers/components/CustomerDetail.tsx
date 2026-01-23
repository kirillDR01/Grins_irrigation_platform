import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Phone, Mail, Edit, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { StatusBadge, LoadingPage, ErrorMessage, PageHeader } from '@/shared/components';
import { useCustomer, useDeleteCustomer } from '../hooks';
import { getCustomerFlags, getCustomerFullName } from '../types';
import { toast } from 'sonner';

interface CustomerDetailProps {
  onEdit?: () => void;
}

export function CustomerDetail({ onEdit }: CustomerDetailProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: customer, isLoading, error, refetch } = useCustomer(id!);
  const deleteMutation = useDeleteCustomer();

  const handleDelete = async () => {
    if (!customer) return;

    if (window.confirm(`Are you sure you want to delete ${getCustomerFullName(customer)}?`)) {
      try {
        await deleteMutation.mutateAsync(customer.id);
        toast.success('Customer deleted successfully');
        navigate('/customers');
      } catch {
        toast.error('Failed to delete customer');
      }
    }
  };

  if (isLoading) {
    return <LoadingPage message="Loading customer..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={() => refetch()} />;
  }

  if (!customer) {
    return <ErrorMessage error={new Error('Customer not found')} />;
  }

  const flags = getCustomerFlags(customer);

  return (
    <div data-testid="customer-detail">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/customers">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Customers
          </Link>
        </Button>
      </div>

      <PageHeader
        title={getCustomerFullName(customer)}
        description={`Customer since ${new Date(customer.created_at).toLocaleDateString()}`}
        action={
          <div className="flex gap-2">
            {onEdit && (
              <Button variant="outline" onClick={onEdit} data-testid="edit-customer-btn">
                <Edit className="mr-2 h-4 w-4" />
                Edit
              </Button>
            )}
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              data-testid="delete-customer-btn"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Contact Information */}
        <Card>
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Phone className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Phone</p>
                <a href={`tel:${customer.phone}`} className="font-medium hover:underline">
                  {customer.phone}
                </a>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                {customer.email ? (
                  <a
                    href={`mailto:${customer.email}`}
                    className="font-medium hover:underline"
                  >
                    {customer.email}
                  </a>
                ) : (
                  <span className="text-muted-foreground">Not provided</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Status & Flags */}
        <Card>
          <CardHeader>
            <CardTitle>Status & Flags</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">Customer Flags</p>
              <div className="flex gap-2 flex-wrap">
                {flags.length > 0 ? (
                  flags.map((flag) => (
                    <StatusBadge key={flag} status={flag} type="customer" />
                  ))
                ) : (
                  <span className="text-muted-foreground">No flags</span>
                )}
              </div>
            </div>
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground mb-2">Communication Preferences</p>
              <div className="space-y-1">
                <p className="text-sm">
                  SMS: {customer.sms_opt_in ? '✓ Opted in' : '✗ Opted out'}
                </p>
                <p className="text-sm">
                  Email: {customer.email_opt_in ? '✓ Opted in' : '✗ Opted out'}
                </p>
              </div>
            </div>
            {customer.lead_source && (
              <>
                <Separator />
                <div>
                  <p className="text-sm text-muted-foreground">Lead Source</p>
                  <p className="font-medium">{customer.lead_source}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Properties - Placeholder */}
        <Card>
          <CardHeader>
            <CardTitle>Properties</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No properties yet.</p>
            <Button variant="outline" size="sm" className="mt-4">
              Add Property
            </Button>
          </CardContent>
        </Card>

        {/* Jobs History - Placeholder */}
        <Card>
          <CardHeader>
            <CardTitle>Job History</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">No jobs yet.</p>
            <Button variant="outline" size="sm" className="mt-4" asChild>
              <Link to={`/jobs?customer_id=${customer.id}`}>View Jobs</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
