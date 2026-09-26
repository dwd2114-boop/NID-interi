"""layout.json -> SketchUp Ruby 스크립트 (surim_101-404.rb) 생성."""
import json
import os

HERE = os.path.dirname(__file__)
data = json.load(open(os.path.join(HERE, "..", "layout.json"), encoding="utf-8"))
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

RB = r'''# encoding: UTF-8
# =============================================================================
#  수림아파트 101동 404호 — 리모델링 평면 3D 모델 (NID종합공사 상세 견적 반영)
#  공급 90㎡ / 전용 72㎡ · 천장고 2,300mm
#
#  사용법 (SketchUp 2017 이상)
#   1) 이 파일과 textures 폴더를 같은 위치에 둡니다.
#   2) SketchUp > 창(Window) > Ruby 콘솔 을 열고 아래 한 줄을 입력합니다.
#        load 'C:/경로/surim_101-404.rb'
#      (또는 확장 프로그램 관리자에서 .rb 를 불러와도 됩니다)
#   3) 새 모델에 벽체·바닥·견적 품목이 그룹으로 생성되고, 장면 탭 2개
#      ("01 평면도(탑뷰)", "02 투시도")가 만들어집니다.
#
#  태그(레이어): 벽체 / 바닥 / 주방 / 욕실 / 현관 / 가구 / 문 / 창호 /
#               몰딩·걸레받이 / 조명·전기 / 인방(상부벽) / 천장·조명(숨김)
#  평면도 장면에서는 인방·천장을 숨겨 위에서 내려다본 평면이 보입니다.
#  그룹 이름 앞의 [번호] 는 상세 견적내역서의 No. 입니다.
# =============================================================================
require 'json'

module NID
  module Surim404
    DIR = File.dirname(__FILE__)
    DATA = JSON.parse(<<'__JSON__')
@@PAYLOAD@@
__JSON__

    def self.pt(x, y, z)
      # 평면 좌표(y 아래 방향) -> SketchUp(y 위 방향)
      Geom::Point3d.new(x.to_f.mm, -y.to_f.mm, z.to_f.mm)
    end

    def self.materials(model)
      mats = {}
      DATA['materials'].each do |key, m|
        mat = model.materials[m['name']] || model.materials.add(m['name'])
        hex = m['color'].delete('#')
        mat.color = Sketchup::Color.new(hex[0, 2].to_i(16), hex[2, 2].to_i(16), hex[4, 2].to_i(16))
        mat.alpha = m['alpha'].to_f if m['alpha'].to_f < 1.0
        if m['tex']
          path = File.join(DIR, 'textures', m['tex'])
          begin
            if File.exist?(path)
              mat.texture = path
              mat.texture.size = [m['texmm'].to_f.mm, m['texmm'].to_f.mm]
            end
          rescue StandardError
            nil # 텍스처를 못 읽으면 단색으로 둔다
          end
        end
        mats[key] = mat
      end
      mats
    end

    def self.solid(ents, pts, height, mat)
      face = ents.add_face(pts)
      return nil unless face
      face.reverse! if face.normal.z < 0
      face.pushpull(height.to_f.mm)
      ents.grep(Sketchup::Face).each { |f| f.material = mat }
      face
    end

    def self.add_box(parent, p, mat)
      g = parent.add_group
      g.name = p['n']
      x0, y0, x1, y1, z0 = p['x0'], p['y0'], p['x1'], p['y1'], p['z0']
      pts = [pt(x0, y0, z0), pt(x1, y0, z0), pt(x1, y1, z0), pt(x0, y1, z0)]
      solid(g.entities, pts, p['z1'] - p['z0'], mat)
      if p['rot']
        c = pt((x0 + x1) / 2.0, (y0 + y1) / 2.0, z0)
        g.transform!(Geom::Transformation.rotation(c, Z_AXIS, -p['rot'].to_f.degrees))
      end
      g
    end

    def self.add_cyl(parent, p, mat)
      g = parent.add_group
      g.name = p['n']
      seg = 24
      pts = (0...seg).map do |i|
        a = 2 * Math::PI * i / seg
        pt(p['cx'] + p['rx'] * Math.cos(a), p['cy'] + p['ry'] * Math.sin(a), p['z0'])
      end
      solid(g.entities, pts, p['z1'] - p['z0'], mat)
      g
    end

    def self.build
      model = Sketchup.active_model
      model.start_operation('수림 101-404 평면 생성', true)
      mats = materials(model)
      root = model.active_entities.add_group
      root.name = DATA['project'] + ' (공급 90㎡ / 전용 72㎡)'

      layers = {}
      groups = {}
      DATA['prims'].each do |p|
        tag = p['tag'].to_s.empty? ? '기타' : p['tag']
        layers[tag] ||= model.layers[tag] || model.layers.add(tag)
        gname = p['grp'].to_s.empty? ? tag : p['grp']
        key = gname + '|' + tag
        unless groups[key]
          grp = root.entities.add_group
          grp.name = gname
          grp.layer = layers[tag]
          groups[key] = grp
        end
        mat = mats[p['m']]
        g = p['k'] == 'box' ? add_box(groups[key].entities, p, mat) : add_cyl(groups[key].entities, p, mat)
        g.layer = layers[tag] if g
      end

      # 실 이름 라벨
      lab = model.layers['라벨'] || model.layers.add('라벨')
      lg = root.entities.add_group
      lg.name = '실 이름'
      lg.layer = lab
      DATA['labels'].each do |l|
        t = lg.entities.add_text("#{l['name']}\n#{l['area']}㎡", pt(l['x'], l['y'], 10))
        t.layer = lab if t
      end

      # 주요 치수
      dl = model.layers['치수'] || model.layers.add('치수')
      dg = root.entities.add_group
      dg.name = '치수'
      dg.layer = dl
      [[0, 1700], [1700, 5200], [5200, 6900], [6900, 9750], [9750, 11350], [0, 11350]].each_with_index do |(a, b), i|
        off = i == 5 ? 1300 : 700
        d = dg.entities.add_dimension_linear(pt(a, 0, 0), pt(b, 0, 0), Geom::Vector3d.new(0, off.mm, 0))
        d.layer = dl if d
      end
      [[0, 2700], [2700, 4100], [4100, 5300], [5300, 6950], [6950, 8400], [0, 8400]].each_with_index do |(a, b), i|
        off = i == 5 ? 1300 : 700
        d = dg.entities.add_dimension_linear(pt(0, a, 0), pt(0, b, 0), Geom::Vector3d.new(-off.mm, 0, 0))
        d.layer = dl if d
      end

      # 그림자 / 장면
      si = model.shadow_info
      si['DisplayShadows'] = true
      si['Light'] = 80
      si['Dark'] = 45
      begin
        si['ShadowTime'] = Time.utc(2026, 10, 15, 5, 0, 0)
      rescue StandardError
        nil
      end

      hidden = ['인방(상부벽)', '천장·조명(숨김)']
      view = model.active_view
      model.layers.each { |l| l.visible = !hidden.include?(l.name) }
      cx = 5675.mm
      cy = -4200.mm
      cam = Sketchup::Camera.new([cx, cy, 30000.mm], [cx, cy, 0], [0, 1, 0])
      cam.perspective = false
      view.camera = cam
      view.zoom_extents
      model.pages.add('01 평면도(탑뷰)')

      model.layers.each { |l| l.visible = !(hidden.include?(l.name) || l.name == '치수' || l.name == '라벨') }
      cam2 = Sketchup::Camera.new([13200.mm, -15200.mm, 13500.mm], [5500.mm, -4300.mm, -600.mm], [0, 0, 1])
      cam2.perspective = true
      cam2.fov = 35
      view.camera = cam2
      model.pages.add('02 투시도')

      model.commit_operation
      model.pages.selected_page = model.pages['01 평면도(탑뷰)']
      UI.messagebox("#{DATA['project']} 모델 생성 완료\n품목 그룹 #{groups.size}개 · 도형 #{DATA['prims'].size}개\n장면: 01 평면도(탑뷰) / 02 투시도")
    rescue StandardError => e
      model.abort_operation if model
      UI.messagebox("모델 생성 오류: #{e.message}")
      raise
    end
  end
end

NID::Surim404.build
'''

out = os.path.join(HERE, "..", "surim_101-404.rb")
open(out, "w", encoding="utf-8").write(RB.replace("@@PAYLOAD@@", payload))
print("->", os.path.abspath(out))
