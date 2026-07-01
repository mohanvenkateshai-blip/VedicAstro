import React from 'react';
import { CharaDashaData } from '../../lib/types';

interface CharaDashaProps {
  data: CharaDashaData;
}

const CharaDasha: React.FC<CharaDashaProps> = ({ data }) => {
  return (
    <div className="chara-dasha">
      <h2>Chara Dasha</h2>
      <div className="dasha-grid">
        {data.charaDashas.map((dasha, index) => (
          <div key={index} className="dasha-item">
            <div className="dasha-name">{dasha.name}</div>
            <div className="dasha-duration">{dasha.duration}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CharaDasha;