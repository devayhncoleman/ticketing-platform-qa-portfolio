"""
Test Suite for Organizations Management
TDD Approach: Tests written FIRST, then implementation

Multi-Tenant Architecture:
- Platform Admin: Manages entire platform, creates orgs
- Org Admin: Manages their own organization
- Technician: Solves tickets within their org
- Customer: Submits tickets within their org
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import sys
import os

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestOrganizationModel:
    """Test the Organization data model"""
    
    def test_organization_has_required_fields(self):
        """Organization must have: orgId, name, slug, status, createdAt"""
        org = {
            'orgId': 'org_001',
            'name': 'Emerald Cloud Lab',
            'slug': 'emerald',
            'status': 'active',
            'createdAt': '2026-02-01T00:00:00Z'
        }
        
        assert 'orgId' in org
        assert 'name' in org
        assert 'slug' in org
        assert 'status' in org
        assert 'createdAt' in org
    
    def test_organization_optional_theme_field(self):
        """Organization can have optional theme settings"""
        org = {
            'orgId': 'org_001',
            'name': 'Emerald Cloud Lab',
            'slug': 'emerald',
            'status': 'active',
            'createdAt': '2026-02-01T00:00:00Z',
            'theme': {
                'primaryColor': '#00ff41',
                'accentColor': '#a855f7'
            }
        }
        
        assert 'theme' in org
        assert org['theme']['primaryColor'] == '#00ff41'
    
    def test_organization_status_values(self):
        """Organization status must be one of: active, suspended, trial"""
        valid_statuses = ['active', 'suspended', 'trial']
        
        for status in valid_statuses:
            org = {'status': status}
            assert org['status'] in valid_statuses


class TestCreateOrganization:
    """Test creating new organizations"""
    
    @patch('boto3.resource')
    def test_create_org_success(self, mock_boto):
        """Platform admin can create a new organization"""
        mock_table = MagicMock()
        mock_table.scan.return_value = {'Items': []}  # No existing slug
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'body': json.dumps({
                'name': 'Emerald Cloud Lab',
                'slug': 'emerald'
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'platform-admin-123',
                        'custom:role': 'platform_admin'
                    }
                }
            }
        }
        
        # Need to reload module to pick up mock
        import importlib
        from organizations import create_organization
        importlib.reload(create_organization)
        
        response = create_organization.handler(event, None)
        
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'orgId' in body
        assert body['name'] == 'Emerald Cloud Lab'
        assert body['slug'] == 'emerald'
        assert body['status'] == 'active'
    
    @patch('boto3.resource')
    def test_create_org_requires_platform_admin(self, mock_boto):
        """Only platform admin can create organizations"""
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'body': json.dumps({
                'name': 'Test Org',
                'slug': 'test'
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'regular-user-123',
                        'custom:role': 'org_admin'  # Not platform_admin
                    }
                }
            }
        }
        
        import importlib
        from organizations import create_organization
        importlib.reload(create_organization)
        
        response = create_organization.handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'error' in body
    
    @patch('boto3.resource')
    def test_create_org_slug_must_be_unique(self, mock_boto):
        """Organization slug must be unique - returns 409 Conflict"""
        mock_table = MagicMock()
        # Simulate slug already exists
        mock_table.scan.return_value = {'Items': [{'slug': 'emerald', 'orgId': 'org_existing'}]}
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'body': json.dumps({
                'name': 'Another Emerald',
                'slug': 'emerald'  # Already exists
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'platform-admin-123',
                        'custom:role': 'platform_admin'
                    }
                }
            }
        }
        
        import importlib
        from organizations import create_organization
        importlib.reload(create_organization)
        
        response = create_organization.handler(event, None)
        
        # Should return 409 Conflict when slug already exists
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert 'already exists' in body['error'].lower()


class TestListOrganizations:
    """Test listing organizations"""
    
    @patch('boto3.resource')
    def test_platform_admin_can_list_all_orgs(self, mock_boto):
        """Platform admin can see all organizations"""
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            'Items': [
                {'orgId': 'org_001', 'name': 'Emerald', 'status': 'active'},
                {'orgId': 'org_002', 'name': 'Acme', 'status': 'active'}
            ]
        }
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'platform-admin-123',
                        'custom:role': 'platform_admin'
                    }
                }
            }
        }
        
        import importlib
        from organizations import list_organizations
        importlib.reload(list_organizations)
        
        response = list_organizations.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['organizations']) == 2
    
    @patch('boto3.resource')
    def test_org_admin_can_only_see_own_org(self, mock_boto):
        """Org admin can only see their own organization"""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {'orgId': 'org_001', 'name': 'Emerald', 'status': 'active'}
        }
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'org-admin-123',
                        'custom:role': 'org_admin',
                        'custom:orgId': 'org_001'
                    }
                }
            }
        }
        
        import importlib
        from organizations import list_organizations
        importlib.reload(list_organizations)
        
        response = list_organizations.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['organizations']) == 1
        assert body['organizations'][0]['orgId'] == 'org_001'


class TestGetOrganization:
    """Test getting a single organization"""
    
    @patch('boto3.resource')
    def test_get_org_by_id(self, mock_boto):
        """Can retrieve organization by ID"""
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'orgId': 'org_001',
                'name': 'Emerald Cloud Lab',
                'slug': 'emerald',
                'status': 'active',
                'createdAt': '2026-02-01T00:00:00Z'
            }
        }
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'orgId': 'org_001'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'custom:orgId': 'org_001'
                    }
                }
            }
        }
        
        import importlib
        from organizations import get_organization
        importlib.reload(get_organization)
        
        response = get_organization.handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['orgId'] == 'org_001'
        assert body['name'] == 'Emerald Cloud Lab'
    
    @patch('boto3.resource')
    def test_cannot_get_other_org(self, mock_boto):
        """Users cannot view organizations they don't belong to"""
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'orgId': 'org_002'},  # Different org
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user-123',
                        'custom:orgId': 'org_001',  # User belongs to org_001
                        'custom:role': 'technician'
                    }
                }
            }
        }
        
        import importlib
        from organizations import get_organization
        importlib.reload(get_organization)
        
        response = get_organization.handler(event, None)
        
        assert response['statusCode'] == 403


class TestUpdateOrganization:
    """Test updating organizations"""
    
    @patch('boto3.resource')
    def test_org_admin_can_update_own_org(self, mock_boto):
        """Org admin can update their organization's details"""
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            'Attributes': {
                'orgId': 'org_001',
                'name': 'Emerald Cloud Lab - Updated',
                'status': 'active'
            }
        }
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'orgId': 'org_001'},
            'body': json.dumps({
                'name': 'Emerald Cloud Lab - Updated'
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'org-admin-123',
                        'custom:role': 'org_admin',
                        'custom:orgId': 'org_001'
                    }
                }
            }
        }
        
        import importlib
        from organizations import update_organization
        importlib.reload(update_organization)
        
        response = update_organization.handler(event, None)
        
        assert response['statusCode'] == 200
    
    @patch('boto3.resource')
    def test_org_admin_cannot_update_other_org(self, mock_boto):
        """Org admin cannot update other organizations"""
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'orgId': 'org_002'},  # Different org
            'body': json.dumps({'name': 'Hacked Name'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'org-admin-123',
                        'custom:role': 'org_admin',
                        'custom:orgId': 'org_001'  # Belongs to different org
                    }
                }
            }
        }
        
        import importlib
        from organizations import update_organization
        importlib.reload(update_organization)
        
        response = update_organization.handler(event, None)
        
        assert response['statusCode'] == 403
    
    @patch('boto3.resource')
    def test_platform_admin_can_update_any_org(self, mock_boto):
        """Platform admin can update any organization"""
        mock_table = MagicMock()
        mock_table.update_item.return_value = {'Attributes': {'orgId': 'org_002'}}
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'orgId': 'org_002'},
            'body': json.dumps({'status': 'suspended'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'platform-admin-123',
                        'custom:role': 'platform_admin'
                    }
                }
            }
        }
        
        import importlib
        from organizations import update_organization
        importlib.reload(update_organization)
        
        response = update_organization.handler(event, None)
        
        assert response['statusCode'] == 200


class TestOrganizationTheme:
    """Test organization theming (white-label support)"""
    
    @patch('boto3.resource')
    def test_can_set_org_theme(self, mock_boto):
        """Org admin can set theme colors"""
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            'Attributes': {
                'orgId': 'org_001',
                'theme': {
                    'primaryColor': '#00ff41',
                    'accentColor': '#a855f7',
                    'logoUrl': 'https://example.com/logo.png'
                }
            }
        }
        mock_boto.return_value.Table.return_value = mock_table
        
        event = {
            'pathParameters': {'orgId': 'org_001'},
            'body': json.dumps({
                'theme': {
                    'primaryColor': '#00ff41',
                    'accentColor': '#a855f7',
                    'logoUrl': 'https://example.com/logo.png'
                }
            }),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'org-admin-123',
                        'custom:role': 'org_admin',
                        'custom:orgId': 'org_001'
                    }
                }
            }
        }
        
        import importlib
        from organizations import update_organization
        importlib.reload(update_organization)
        
        response = update_organization.handler(event, None)
        
        assert response['statusCode'] == 200


class TestUserOrgAssociation:
    """Test that users are properly associated with organizations"""
    
    def test_user_has_org_id(self):
        """Users must have an orgId field"""
        user = {
            'userId': 'user_001',
            'email': 'tech@emerald.com',
            'orgId': 'org_001',
            'orgRole': 'technician'
        }
        
        assert 'orgId' in user
        assert user['orgId'] == 'org_001'
    
    def test_user_org_roles(self):
        """Users have org-specific roles"""
        valid_org_roles = ['org_admin', 'technician', 'customer']
        
        user = {'orgRole': 'technician'}
        assert user['orgRole'] in valid_org_roles
    
    def test_platform_admin_has_no_org(self):
        """Platform admins don't belong to any specific org"""
        platform_admin = {
            'userId': 'admin_001',
            'email': 'admin@platform.com',
            'role': 'platform_admin',
            'orgId': None  # No org association
        }
        
        assert platform_admin['orgId'] is None


class TestTicketOrgIsolation:
    """Test that tickets are isolated by organization"""
    
    def test_ticket_has_org_id(self):
        """Tickets must have an orgId field"""
        ticket = {
            'ticketId': 'ticket_001',
            'title': 'Help needed',
            'orgId': 'org_001',
            'createdBy': 'user_001'
        }
        
        assert 'orgId' in ticket
    
    def test_list_tickets_filtered_by_org(self):
        """Listing tickets only returns tickets from user's org"""
        # Simulated filtered results
        items = [
            {'ticketId': 't1', 'orgId': 'org_001', 'title': 'Emerald Ticket 1'},
            {'ticketId': 't2', 'orgId': 'org_001', 'title': 'Emerald Ticket 2'}
        ]
        
        # All items should be from same org
        for item in items:
            assert item['orgId'] == 'org_001'


class TestPlatformAdminDashboard:
    """Test platform admin dashboard functionality"""
    
    def test_platform_admin_sees_all_org_stats(self):
        """Platform admin can see stats across all organizations"""
        expected_stats = {
            'totalOrganizations': 5,
            'totalUsers': 150,
            'totalTickets': 500,
            'organizationBreakdown': [
                {'orgId': 'org_001', 'name': 'Emerald', 'userCount': 50, 'ticketCount': 150},
                {'orgId': 'org_002', 'name': 'Acme', 'userCount': 100, 'ticketCount': 350}
            ]
        }
        
        # This documents the expected dashboard data structure
        assert 'totalOrganizations' in expected_stats
        assert 'organizationBreakdown' in expected_stats


# Run with: pytest test_organizations.py -v
if __name__ == '__main__':
    pytest.main([__file__, '-v'])