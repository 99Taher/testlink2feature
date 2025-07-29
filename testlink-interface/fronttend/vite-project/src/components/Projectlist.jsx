// frontend/src/components/ProjectList.jsx
import { useEffect, useState } from "react";
import axios from "axios";

function ProjectList() {
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    axios.get("http://localhost:5000/projects")
         .then(res => setProjects(res.data))
         .catch(err => console.error(err));
  }, []);

  return (
    <div>
      <h2>Liste des Projets</h2>
      <ul>
        {projects.map(p => (
          <li key={p.id}>{p.name}</li>
        ))}
      </ul>
    </div>
  );
}

export default ProjectList;