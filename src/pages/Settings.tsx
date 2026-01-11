const Settings = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-base-content">Settings</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Account Settings */}
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Account Settings</h2>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Email Notifications</span>
              </label>
              <div className="flex items-center space-x-2">
                <input type="checkbox" className="toggle toggle-primary" defaultChecked />
                <span className="text-sm">Receive email notifications</span>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Two-Factor Authentication</span>
              </label>
              <div className="flex items-center space-x-2">
                <input type="checkbox" className="toggle toggle-primary" />
                <span className="text-sm">Enable 2FA</span>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Language</span>
              </label>
              <select className="select select-bordered">
                <option>English</option>
                <option>Spanish</option>
                <option>French</option>
                <option>German</option>
              </select>
            </div>
          </div>
        </div>

        {/* Security Settings */}
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Security</h2>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Current Password</span>
              </label>
              <input type="password" className="input input-bordered" />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">New Password</span>
              </label>
              <input type="password" className="input input-bordered" />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Confirm New Password</span>
              </label>
              <input type="password" className="input input-bordered" />
            </div>

            <div className="card-actions justify-end">
              <button className="btn btn-primary">Update Password</button>
            </div>
          </div>
        </div>

        {/* Theme Settings */}
        <div className="card bg-base-100 shadow-xl">
          <div className="card-body">
            <h2 className="card-title">Appearance</h2>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Theme</span>
              </label>
              <div className="flex space-x-2">
                <button className="btn btn-outline">Light</button>
                <button className="btn btn-primary">Dark</button>
                <button className="btn btn-outline">Auto</button>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text">Compact Mode</span>
              </label>
              <div className="flex items-center space-x-2">
                <input type="checkbox" className="toggle toggle-primary" />
                <span className="text-sm">Enable compact layout</span>
              </div>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="card bg-base-100 shadow-xl border-error">
          <div className="card-body">
            <h2 className="card-title text-error">Danger Zone</h2>
            <p className="text-sm text-base-content/70 mb-4">
              These actions cannot be undone. Please be careful.
            </p>

            <div className="card-actions justify-end">
              <button className="btn btn-outline btn-error">Delete Account</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;