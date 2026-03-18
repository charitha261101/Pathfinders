import jsonfile from "jsonfile";
import moment from "moment";  

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';
 const path = "./data.json";
 const date = moment().format();
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
 
const data = {
  date : date, 
}

jsonfile.writeFile(path,data);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
