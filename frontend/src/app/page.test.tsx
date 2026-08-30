import { render, screen } from '@testing-library/react';
import HomePage from './page';

describe('HomePage', () => {
  it('renders the sign in panel', () => {
    render(<HomePage />);
    expect(screen.getByText('AI Workspace')).toBeInTheDocument();
    expect(screen.getByText('Secure knowledge workspace')).toBeInTheDocument();
  });
});
