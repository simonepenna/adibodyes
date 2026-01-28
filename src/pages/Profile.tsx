import { useEffect } from 'react';

const Profile = () => {
  // Aggiorna il titolo della pagina
  useEffect(() => {
    document.title = 'AdiBody ES - Profile';
  }, []);
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-base-content">Profile</h1>
        <button className="btn btn-primary">Edit Profile</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Info */}
        <div className="lg:col-span-1">
          <div className="card bg-base-100 shadow-xl">
            <div className="card-body items-center text-center">
              <div className="avatar">
                <div className="w-24 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
                  <img src="https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp" alt="Profile" />
                </div>
              </div>
              <h2 className="card-title">John Doe</h2>
              <p className="text-base-content/70">Administrator</p>
              <div className="card-actions justify-center">
                <button className="btn btn-outline btn-sm">Change Photo</button>
              </div>
            </div>
          </div>
        </div>

        {/* Profile Details */}
        <div className="lg:col-span-2">
          <div className="card bg-base-100 shadow-xl">
            <div className="card-body">
              <h2 className="card-title">Personal Information</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-control">
                  <label className="label">
                    <span className="label-text">First Name</span>
                  </label>
                  <input type="text" placeholder="John" className="input input-bordered" />
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Last Name</span>
                  </label>
                  <input type="text" placeholder="Doe" className="input input-bordered" />
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Email</span>
                  </label>
                  <input type="email" placeholder="john@example.com" className="input input-bordered" />
                </div>

                <div className="form-control">
                  <label className="label">
                    <span className="label-text">Phone</span>
                  </label>
                  <input type="tel" placeholder="+1 (555) 123-4567" className="input input-bordered" />
                </div>
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text">Bio</span>
                </label>
                <textarea
                  className="textarea textarea-bordered h-24"
                  placeholder="Tell us about yourself..."
                ></textarea>
              </div>

              <div className="card-actions justify-end">
                <button className="btn btn-ghost">Cancel</button>
                <button className="btn btn-primary">Save Changes</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;